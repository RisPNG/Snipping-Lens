from click import ClickException
from datasette import hookimpl
from datasette.utils.asgi import Response, NotFound, Forbidden
from datasette.plugins import pm
from graphql import graphql, print_schema
import json
from .utils import schema_for_database_via_cache
from . import hookspecs
import pathlib
import time
import urllib

pm.add_hookspecs(hookspecs)

DEFAULT_TIME_LIMIT_MS = 1000
DEFAULT_NUM_QUERIES_LIMIT = 100


async def post_body(request):
    body = b""
    more_body = True
    while more_body:
        message = await request.receive()
        assert message["type"] == "http.request", message
        body += message.get("body", b"")
        more_body = message.get("more_body", False)

    return body


async def view_graphql_schema(request, datasette):
    database = request.url_vars.get("database")
    try:
        db = datasette.get_database(database)
    except KeyError:
        raise NotFound("Database does not exist")
    await check_permissions(request, datasette, db.name)
    schema = await schema_for_database_via_cache(datasette, database=database)
    return Response.text(print_schema(schema.schema.graphql_schema))


CORS_HEADERS = {
    "Access-Control-Allow-Headers": "content-type",
    "Access-Control-Allow-Method": "POST",
    "Access-Control-Allow-Origin": "*",
    "Vary": "accept",
}


async def view_graphql(request, datasette):
    if request.method == "OPTIONS":
        return Response.text("ok", headers=CORS_HEADERS if datasette.cors else {})

    body = await post_body(request)
    database = request.url_vars.get("database")

    try:
        db = datasette.get_database(database)
    except KeyError:
        raise NotFound("Database does not exist")

    await check_permissions(request, datasette, db.name)

    if not body and "text/html" in request.headers.get("accept", ""):
        static = pathlib.Path(__file__).parent / "static"
        js_filenames = [p.name for p in static.glob("*.js")]
        # These need to be sorted so react loads first
        order = "react", "react-dom", "graphiql"
        js_filenames.sort(key=lambda filename: order.index(filename.split(".")[0]))
        return Response.html(
            await datasette.render_template(
                "graphiql.html",
                {
                    "database": database,
                    "graphiql_css": [p.name for p in static.glob("*.css")],
                    "graphiql_js": js_filenames,
                },
                request=request,
            ),
            headers=CORS_HEADERS if datasette.cors else {},
        )

    schema = (await schema_for_database_via_cache(datasette, database=database)).schema

    if request.args.get("schema"):
        return Response.text(print_schema(schema.graphql_schema))

    incoming = {}
    if body:
        incoming = json.loads(body)
        query = incoming.get("query")
        variables = incoming.get("variables")
        operation_name = incoming.get("operationName")
    else:
        query = request.args.get("query")
        variables = request.args.get("variables", "")
        if variables:
            variables = json.loads(variables)
        operation_name = request.args.get("operationName")

    if not query:
        return Response.json(
            {"error": "Missing query"},
            status=400,
            headers=CORS_HEADERS if datasette.cors else {},
        )

    config = datasette.plugin_config("datasette-graphql") or {}
    context = {
        "time_started": time.monotonic(),
        "time_limit_ms": config.get("time_limit_ms") or DEFAULT_TIME_LIMIT_MS,
        "num_queries_executed": 0,
        "num_queries_limit": config.get("num_queries_limit")
        or DEFAULT_NUM_QUERIES_LIMIT,
    }

    result = await schema.execute_async(
        query,
        operation_name=operation_name,
        variable_values=variables or {},
        context_value=context,
    )
    response = {"data": result.data}
    if result.errors:
        response["errors"] = [error.formatted for error in result.errors]

    return Response.json(
        response,
        status=200 if not result.errors else 500,
        headers=CORS_HEADERS if datasette.cors else {},
    )


async def check_permissions(request, datasette, database):
    # First check database permission
    ok = await datasette.permission_allowed(
        request.actor,
        "view-database",
        resource=database,
        default=None,
    )
    if ok is not None:
        if ok:
            return
        else:
            raise Forbidden("view-database")

    # Fall back to checking instance permission
    ok2 = await datasette.permission_allowed(
        request.actor,
        "view-instance",
        default=None,
    )
    if ok2 is False:
        raise Forbidden("view-instance")


@hookimpl
def menu_links(datasette, actor):
    return [
        {"href": datasette.urls.path("/graphql"), "label": "GraphQL API"},
    ]


@hookimpl
def register_routes():
    return [
        (r"^/graphql/(?P<database>[^/]+)\.graphql$", view_graphql_schema),
        (r"^/graphql/(?P<database>[^/]+)$", view_graphql),
        (r"^/graphql$", view_graphql),
    ]


@hookimpl
def extra_template_vars(datasette):
    async def graphql_template_tag(query, database=None, variables=None):
        schema = (
            await schema_for_database_via_cache(datasette, database=database)
        ).schema
        result = await schema.execute_async(
            query,
            variable_values=variables or {},
        )
        if result.errors:
            raise Exception(result.errors)
        else:
            return result.data

    return {
        "graphql": graphql_template_tag,
    }


@hookimpl
def startup(datasette):
    # Validate configuration
    config = datasette.plugin_config("datasette-graphql") or {}
    if "databases" in config:
        for database_name in config["databases"].keys():
            try:
                datasette.get_database(database_name)
            except KeyError:
                raise ClickException(
                    "datasette-graphql config error: '{}' is not a connected database".format(
                        database_name
                    )
                )


@hookimpl
def table_actions(datasette, actor, database, table):
    async def inner():
        graphql_path = datasette.urls.path("/graphql/{}".format(database))
        db_schema = await schema_for_database_via_cache(datasette, database=database)
        try:
            example_query = await db_schema.table_classes[table].example_query()
        except KeyError:
            # https://github.com/simonw/datasette-graphql/issues/90
            return []
        return [
            {
                "href": "{}?query={}".format(
                    graphql_path, urllib.parse.quote(example_query)
                ),
                "label": "GraphQL API for {}".format(table),
            }
        ]

    return inner


@hookimpl
def database_actions(datasette, actor, database):
    if len(datasette.databases) > 1:
        return [
            {
                "href": datasette.urls.path("/graphql/{}".format(database)),
                "label": "GraphQL API for {}".format(database),
            }
        ]
    else:
        return [
            {
                "href": datasette.urls.path("/graphql"),
                "label": "GraphQL API",
            }
        ]
