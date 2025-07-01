from base64 import b64decode, b64encode
from collections import namedtuple
from datasette.utils import await_me_maybe
from datasette.plugins import pm
from enum import Enum
import graphene
from graphene.types import generic
import json
import keyword
import urllib
import re
import sqlite_utils
import textwrap
import time

TableMetadata = namedtuple(
    "TableMetadata",
    (
        "columns",
        "foreign_keys",
        "fks_back",
        "pks",
        "supports_fts",
        "is_view",
        "graphql_name",
        "graphql_columns",
    ),
)


class Bytes(graphene.Scalar):
    # Replace with graphene.Base64 after graphene 3.0 is released
    @staticmethod
    def serialize(value):
        if isinstance(value, bytes):
            return b64encode(value).decode("utf-8")
        return value

    @classmethod
    def parse_literal(cls, node):
        if isinstance(node, ast.StringValue):
            return cls.parse_value(node.value)

    @staticmethod
    def parse_value(value):
        if isinstance(value, bytes):
            return value
        else:
            return b64decode(value)


types = {
    str: graphene.String(),
    float: graphene.Float(),
    int: graphene.Int(),
    bytes: Bytes(),
}


class PageInfo(graphene.ObjectType):
    endCursor = graphene.String()
    hasNextPage = graphene.Boolean()


class DatabaseSchema:
    def __init__(self, schema, table_classes, table_collection_classes):
        self.schema = schema
        self.table_classes = table_classes
        self.table_collection_classes = table_collection_classes


# cache keys are (database, schema_version) tuples
_schema_cache = {}


async def schema_for_database_via_cache(datasette, database=None):
    db = datasette.get_database(database)
    schema_version = (await db.execute("PRAGMA schema_version")).first()[0]
    cache_key = (database, schema_version)
    if cache_key not in _schema_cache:
        schema = await schema_for_database(datasette, database)
        _schema_cache[cache_key] = schema
        # Delete other cached versions of this database
        to_delete = [
            key for key in _schema_cache if key[0] == database and key != cache_key
        ]
        for key in to_delete:
            del _schema_cache[key]
    return _schema_cache[cache_key]


async def schema_for_database(datasette, database=None):
    db = datasette.get_database(database)
    hidden_tables = await db.hidden_table_names()

    # Perform all introspection in a single call to the execute_fn thread
    table_metadata = await db.execute_fn(
        lambda conn: introspect_tables(conn, datasette, db.name)
    )

    # Construct the tableFilter classes
    table_filters = {
        table: make_table_filter_class(table, meta)
        for table, meta in table_metadata.items()
    }
    # And the table_collection_kwargs
    table_collection_kwargs = {}

    for table, meta in table_metadata.items():
        column_names = meta.graphql_columns.values()
        options = list(zip(column_names, column_names))
        sort_enum = graphene.Enum.from_enum(
            Enum("{}Sort".format(meta.graphql_name), options),
            description="Sort by this column",
        )
        sort_desc_enum = graphene.Enum.from_enum(
            Enum("{}SortDesc".format(meta.graphql_name), options),
            description="Sort by this column descending",
        )
        kwargs = dict(
            filter=graphene.List(
                table_filters[table],
                description='Filters e.g. {name: {eq: "datasette"}}',
            ),
            where=graphene.String(
                description="Extra SQL where clauses, e.g. \"name='datasette'\""
            ),
            first=graphene.Int(description="Number of results to return"),
            after=graphene.String(
                description="Start at this pagination cursor (from tableInfo { endCursor })"
            ),
            sort=sort_enum(),
            sort_desc=sort_desc_enum(),
        )
        if meta.supports_fts:
            kwargs["search"] = graphene.String(description="Search for this term")
        table_collection_kwargs[table] = kwargs

    # For each table, expose a graphene.List
    to_add = []
    table_classes = {}
    table_collection_classes = {}

    for (table, meta) in table_metadata.items():
        table_name = meta.graphql_name
        if table in hidden_tables:
            continue

        # (columns, foreign_keys, fks_back, pks, supports_fts) = table_meta
        table_node_class = await make_table_node_class(
            datasette,
            db,
            table,
            table_classes,
            table_filters,
            table_metadata,
            table_collection_classes,
            table_collection_kwargs,
        )
        table_classes[table] = table_node_class

        # We also need a table collection class - this is the thing with the
        # nodes, edges, pageInfo and totalCount fields for that table
        table_collection_class = make_table_collection_class(
            table, table_node_class, meta
        )
        table_collection_classes[table] = table_collection_class
        to_add.append(
            (
                meta.graphql_name,
                graphene.Field(
                    table_collection_class,
                    **table_collection_kwargs[table],
                    description="Rows from the {} {}".format(
                        table, "view" if table_metadata[table].is_view else "table"
                    )
                ),
            )
        )
        to_add.append(
            (
                "resolve_{}".format(meta.graphql_name),
                make_table_resolver(
                    datasette, db.name, table, table_classes, table_metadata
                ),
            )
        )
        # *_row field
        table_row_kwargs = dict(table_collection_kwargs[table])
        table_row_kwargs.pop("first")
        # Add an argument for each primary key
        for pk in meta.pks:
            if pk == "rowid" and pk not in meta.columns:
                pk_column_type = graphene.Int()
            else:
                pk_column_type = types[meta.columns[pk]]
            table_row_kwargs[meta.graphql_columns.get(pk, pk)] = pk_column_type

        to_add.append(
            (
                "{}_row".format(meta.graphql_name),
                graphene.Field(
                    table_node_class,
                    args=table_row_kwargs,
                    description="Single row from the {} {}".format(
                        table, "view" if table_metadata[table].is_view else "table"
                    ),
                ),
            )
        )
        to_add.append(
            (
                "resolve_{}_row".format(meta.graphql_name),
                make_table_resolver(
                    datasette,
                    db.name,
                    table,
                    table_classes,
                    table_metadata,
                    pk_args=meta.pks,
                    return_first_row=True,
                ),
            )
        )

    if not to_add:
        # Empty schema throws a 500 error, so add something here
        to_add.append(("empty", graphene.String()))
        to_add.append(("resolve_empty", lambda a, b: "schema"))

    for extra_fields in pm.hook.graphql_extra_fields(
        datasette=datasette, database=db.name
    ):
        extra_tuples = await await_me_maybe(extra_fields)
        if extra_tuples:
            to_add.extend(extra_tuples)

    Query = type(
        "Query",
        (graphene.ObjectType,),
        {key: value for key, value in to_add},
    )
    database_schema = DatabaseSchema(
        schema=graphene.Schema(
            query=Query,
            auto_camelcase=(datasette.plugin_config("datasette-graphql") or {}).get(
                "auto_camelcase", False
            ),
        ),
        table_classes=table_classes,
        table_collection_classes=table_collection_classes,
    )
    return database_schema


def make_table_collection_class(table, table_class, meta):
    table_name = meta.graphql_name

    class _Edge(graphene.ObjectType):
        cursor = graphene.String()
        node = graphene.Field(table_class)

        class Meta:
            name = "{}Edge".format(table_name)

    class _TableCollection(graphene.ObjectType):
        totalCount = graphene.Int()
        pageInfo = graphene.Field(PageInfo)
        nodes = graphene.List(table_class)
        edges = graphene.List(_Edge)

        def resolve_totalCount(parent, info):
            return parent["filtered_table_rows_count"]

        def resolve_nodes(parent, info):
            return parent["rows"]

        def resolve_edges(parent, info):
            return [
                {
                    "cursor": path_from_row_pks(row, meta.pks, use_rowid=not meta.pks),
                    "node": row,
                }
                for row in parent["rows"]
            ]

        def resolve_pageInfo(parent, info):
            return {
                "endCursor": parent["next"],
                "hasNextPage": parent["next"] is not None,
            }

        class Meta:
            name = "{}Collection".format(table_name)

    return _TableCollection


class StringOperations(graphene.InputObjectType):
    exact = graphene.String(name="eq", description="Exact match")
    not_ = graphene.String(name="not", description="Not exact match")
    contains = graphene.String(description="String contains")
    endswith = graphene.String(description="String ends with")
    startswith = graphene.String(description="String starts with")
    gt = graphene.String(description="is greater than")
    gte = graphene.String(description="is greater than or equal to")
    lt = graphene.String(description="is less than")
    lte = graphene.String(description="is less than or equal to")
    like = graphene.String(description=r"is like (% for wildcards)")
    notlike = graphene.String(description="is not like")
    glob = graphene.String(description="glob matches (* for wildcards)")
    in_ = graphene.List(graphene.String, name="in", description="in this list")
    notin = graphene.List(graphene.String, description="not in this list")
    arraycontains = graphene.String(description="JSON array contains this value")
    date = graphene.String(description="Value is a datetime on this date")
    isnull = graphene.Boolean(description="Value is null")
    notnull = graphene.Boolean(description="Value is not null")
    isblank = graphene.Boolean(description="Value is null or blank")
    notblank = graphene.Boolean(description="Value is not null or blank")


class IntegerOperations(graphene.InputObjectType):
    exact = graphene.Int(name="eq", description="Exact match")
    not_ = graphene.Int(name="not", description="Not exact match")
    gt = graphene.Int(description="is greater than")
    gte = graphene.Int(description="is greater than or equal to")
    lt = graphene.Int(description="is less than")
    lte = graphene.Int(description="is less than or equal to")
    in_ = graphene.List(graphene.Int, name="in", description="in this list")
    notin = graphene.List(graphene.Int, description="not in this list")
    arraycontains = graphene.Int(description="JSON array contains this value")
    isnull = graphene.Boolean(description="Value is null")
    notnull = graphene.Boolean(description="Value is not null")
    isblank = graphene.Boolean(description="Value is null or blank")
    notblank = graphene.Boolean(description="Value is not null or blank")


types_to_operations = {
    str: StringOperations,
    int: IntegerOperations,
    float: IntegerOperations,
}


def make_table_filter_class(table, meta):
    return type(
        "{}Filter".format(meta.graphql_name),
        (graphene.InputObjectType,),
        {
            meta.graphql_columns[column]: (
                types_to_operations.get(column_type) or StringOperations
            )()
            for column, column_type in meta.columns.items()
        },
    )


async def make_table_node_class(
    datasette,
    db,
    table,
    table_classes,
    table_filters,
    table_metadata,
    table_collection_classes,
    table_collection_kwargs,
):
    meta = table_metadata[table]
    fks_by_column = {fk.column: fk for fk in meta.foreign_keys}

    table_plugin_config = datasette.plugin_config(
        "datasette-graphql", database=db.name, table=table
    )
    json_columns = []
    if table_plugin_config and "json_columns" in table_plugin_config:
        json_columns = table_plugin_config["json_columns"]

    # Create a node class for this table
    plain_columns = []
    fk_columns = []
    table_dict = {}
    if meta.pks == ["rowid"]:
        table_dict["rowid"] = graphene.Int()
        plain_columns.append("rowid")

    columns_to_graphql_names = {}

    for colname, coltype in meta.columns.items():
        graphql_name = meta.graphql_columns[colname]
        columns_to_graphql_names[colname] = graphql_name
        if colname in fks_by_column:
            fk = fks_by_column[colname]
            fk_columns.append((graphql_name, fk.other_table, fk.other_column))
            table_dict[graphql_name] = graphene.Field(
                make_table_getter(table_classes, fk.other_table)
            )
            table_dict["resolve_{}".format(graphql_name)] = make_fk_resolver(
                db, table, table_classes, fk
            )
        else:
            plain_columns.append(graphql_name)
            if colname in json_columns:
                table_dict[graphql_name] = generic.GenericScalar()
                table_dict["resolve_{}".format(graphql_name)] = resolve_generic
            else:
                table_dict[graphql_name] = types[coltype]

    # Now add the backwards foreign key fields for related items
    fk_table_counts = {}
    for fk in meta.fks_back:
        fk_table_counts[fk.table] = fk_table_counts.get(fk.table, 0) + 1
    for fk in meta.fks_back:
        filter_class = table_filters[fk.table]
        if fk_table_counts[fk.table] > 1:
            field_name = "{}_by_{}_list".format(
                table_metadata[fk.table].graphql_name,
                table_metadata[fk.table].graphql_columns[fk.column],
            )
            field_description = "Related rows from the {} table (by {})".format(
                fk.table, fk.column
            )
        else:
            field_name = "{}_list".format(table_metadata[fk.table].graphql_name)
            field_description = "Related rows from the {} table".format(fk.table)
        table_dict[field_name] = graphene.Field(
            make_table_collection_getter(table_collection_classes, fk.table),
            **table_collection_kwargs[fk.table],
            description=field_description
        )
        table_dict["resolve_{}".format(field_name)] = make_table_resolver(
            datasette,
            db.name,
            fk.table,
            table_classes,
            table_metadata,
            related_fk=fk,
        )

    table_dict["from_row"] = classmethod(
        lambda cls, row: cls(
            **dict([(meta.graphql_columns.get(k, k), v) for k, v in dict(row).items()])
        )
    )

    table_dict["graphql_name_for_column"] = columns_to_graphql_names.get

    async def example_query():
        example_query_columns = ["      {}".format(c) for c in plain_columns]
        # Now add the foreign key columns
        for graphql_name, other_table, other_column in fk_columns:
            label_column = await db.label_column_for_table(other_table)
            # Need to find outthe GraphQL names of other_column (the pk) and
            # label_column on other_table
            other_table_obj = table_classes[other_table]
            example_query_columns.append(
                "      %s {\n        %s\n%s      }"
                % (
                    graphql_name,
                    other_table_obj.graphql_name_for_column(other_column),
                    (
                        "        %s\n"
                        % other_table_obj.graphql_name_for_column(label_column)
                    )
                    if label_column
                    else "",
                )
            )
        return (
            textwrap.dedent(
                """
        {
          TABLE {
            totalCount
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
        COLUMNS
            }
          }
        }
        """
            )
            .strip()
            .replace("TABLE", meta.graphql_name)
            .replace("COLUMNS", "\n".join(example_query_columns))
        )

    table_dict["example_query"] = example_query

    return type(meta.graphql_name, (graphene.ObjectType,), table_dict)


def make_table_resolver(
    datasette,
    database_name,
    table_name,
    table_classes,
    table_metadata,
    related_fk=None,
    pk_args=None,
    return_first_row=False,
):
    meta = table_metadata[table_name]

    async def resolve_table(
        root,
        info,
        filter=None,
        where=None,
        first=None,
        after=None,
        search=None,
        sort=None,
        sort_desc=None,
        **kwargs
    ):
        if first is None:
            first = 10

        if return_first_row:
            first = 1

        pairs = []
        column_name_rev = {v: k for k, v in meta.graphql_columns.items()}
        for filter_ in filter or []:
            for column_name, operations in filter_.items():
                for operation_name, value in operations.items():
                    if isinstance(value, list):
                        value = ",".join(map(str, value))
                    pairs.append(
                        [
                            "{}__{}".format(
                                column_name_rev[column_name], operation_name.rstrip("_")
                            ),
                            value,
                        ]
                    )

        if pk_args is not None:
            for pk in pk_args:
                if kwargs.get(pk) is not None:
                    pairs.append([pk, kwargs[pk]])

        qs = {
            "_nofacet": 1,
        }
        qs.update(pairs)
        if after:
            qs["_next"] = after
        qs["_size"] = first

        if search and meta.supports_fts:
            qs["_search"] = search

        if related_fk:
            related_column = meta.graphql_columns.get(
                related_fk.column, related_fk.column
            )
            related_other_column = table_metadata[
                related_fk.other_table
            ].graphql_columns.get(related_fk.other_column, related_fk.other_column)
            qs[related_column] = getattr(root, related_other_column)

        if where:
            qs["_where"] = where
        if sort:
            qs["_sort"] = column_name_rev[sort.value]
        elif sort_desc:
            qs["_sort_desc"] = column_name_rev[sort_desc.value]

        path_with_query_string = "/{}/{}.json?{}".format(
            database_name, table_name, urllib.parse.urlencode(qs)
        )

        context = info.context
        if context and "time_started" in context:
            elapsed_ms = (time.monotonic() - context["time_started"]) * 1000
            if context["time_limit_ms"] and elapsed_ms > context["time_limit_ms"]:
                assert False, "Time limit exceeded: {:.2f}ms > {}ms - {}".format(
                    elapsed_ms, context["time_limit_ms"], path_with_query_string
                )
            context["num_queries_executed"] += 1
            if (
                context["num_queries_limit"]
                and context["num_queries_executed"] > context["num_queries_limit"]
            ):
                assert False, "Query limit exceeded: {} > {} - {}".format(
                    context["num_queries_executed"],
                    context["num_queries_limit"],
                    path_with_query_string,
                )

        data = (await datasette.client.get(path_with_query_string)).json()
        data["rows"] = [dict(zip(data["columns"], row)) for row in data["rows"]]
        # If any cells are $base64, decode them into bytes objects
        for row in data["rows"]:
            for key, value in row.items():
                if isinstance(value, dict) and value.get("$base64"):
                    row[key] = b64decode(value["encoded"])
        klass = table_classes[table_name]
        data["rows"] = [klass.from_row(r) for r in data["rows"]]
        if return_first_row:
            try:
                return data["rows"][0]
            except IndexError:
                return None
        else:
            return data

    return resolve_table


def make_fk_resolver(db, table, table_classes, fk):
    async def resolve_foreign_key(parent, info):
        # retrieve the correct column from parent
        pk = getattr(parent, fk.column)
        sql = "select * from [{}] where [{}] = :v".format(
            fk.other_table, fk.other_column
        )
        params = {"v": pk}
        results = await db.execute(sql, params)
        fk_class = table_classes[fk.other_table]
        try:
            return [fk_class.from_row(row) for row in results.rows][0]
        except IndexError:
            return None

    return resolve_foreign_key


def make_table_getter(table_classes, table):
    def getter():
        return table_classes[table]

    return getter


def make_table_collection_getter(table_collection_classes, table):
    def getter():
        return table_collection_classes[table]

    return getter


def path_from_row_pks(row, pks, use_rowid, quote=True):
    """Generate an optionally URL-quoted unique identifier
    for a row from its primary keys."""
    if use_rowid:
        bits = [row.rowid]
    else:
        bits = [getattr(row, pk) for pk in pks]
    if quote:
        bits = [urllib.parse.quote_plus(str(bit)) for bit in bits]
    else:
        bits = [str(bit) for bit in bits]

    return ",".join(bits)


def introspect_tables(conn, datasette, db_name):
    db = sqlite_utils.Database(conn)

    table_names = db.table_names()
    view_names = db.view_names()

    table_metadata = {}
    table_namer = Namer("t")

    for table in table_names + view_names:
        datasette_table_metadata = datasette.table_metadata(
            table=table, database=db_name
        )
        columns = db[table].columns_dict
        foreign_keys = []
        pks = []
        supports_fts = bool(datasette_table_metadata.get("fts_table"))
        fks_back = []
        if hasattr(db[table], "foreign_keys"):
            # Views don't have .foreign_keys
            foreign_keys = [
                fk
                for fk in db[table].foreign_keys
                # filter out keys to tables that do not exist
                if fk.other_table in table_names
            ]
            pks = db[table].pks
            supports_fts = bool(db[table].detect_fts()) or supports_fts
            # Gather all foreign keys pointing back here
            collected = []
            for t in db.tables:
                collected.extend(t.foreign_keys)
            fks_back = [f for f in collected if f.other_table == table]
        is_view = table in view_names
        column_namer = Namer("c")
        table_metadata[table] = TableMetadata(
            columns=columns,
            foreign_keys=foreign_keys,
            fks_back=fks_back,
            pks=pks,
            supports_fts=supports_fts,
            is_view=is_view,
            graphql_name=table_namer.name(table),
            graphql_columns={column: column_namer.name(column) for column in columns},
        )

    return table_metadata


def resolve_generic(root, info):
    json_string = getattr(root, info.field_name, "")
    return json.loads(json_string)


_invalid_chars_re = re.compile(r"[^_a-zA-Z0-9]")


class Namer:
    def __init__(self, underscore_prefix=""):
        # Disallow all Python keywords
        # https://github.com/simonw/datasette-graphql/issues/84
        self.reserved = set(keyword.kwlist)
        # 'description' confuses Graphene
        # https://github.com/simonw/datasette-graphql/issues/85
        self.reserved.add("description")
        # Track names we have already issued:
        self.names = set()
        self.underscore_prefix = underscore_prefix

    def name(self, value):
        value = "_".join(value.split())
        value = _invalid_chars_re.sub("_", value)
        if not value:
            value = "_"
        if value[0].isdigit():
            value = "_" + value
        if value in self.reserved:
            value += "_"
        suffix = 2
        orig = value
        if value.startswith("_") and value.endswith("_"):
            value = self.underscore_prefix + value
        while value in self.names:
            value = orig + "_" + str(suffix)
            suffix += 1
        self.names.add(value)
        return value
