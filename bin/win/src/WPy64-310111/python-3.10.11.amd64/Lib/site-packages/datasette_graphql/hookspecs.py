from pluggy import HookspecMarker

hookspec = HookspecMarker("datasette")


@hookspec
def graphql_extra_fields(datasette, database):
    "A list of (name, field_type) tuples to include in the GraphQL schema"
