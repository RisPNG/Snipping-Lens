from flask_restx import Resource
from flask import request
from flask_restx import Namespace
from flask_accepts import accepts, responds
from flask.wrappers import Response
from typing import List

from .schema import {{ capitalize(name) }}Schema
from .model import {{ capitalize(name) }}
from .service import {{ capitalize(name) }}Service

api = Namespace("{{ capitalize(name) }}", description="{{ capitalize(name) }} information")


@api.route("/")
class {{ capitalize(name) }}Resource(Resource):
    """{{ capitalize(name) }}s"""

    @responds(schema={{ capitalize(name) }}Schema, many=True)
    def get(self) -> List[{{ capitalize(name) }}]:
        """Get all {{ capitalize(name) }}s"""

        return {{ capitalize(name) }}Service.get_all()

    @accepts(schema={{ capitalize(name) }}Schema, api=api)
    @responds(schema={{ capitalize(name) }}Schema)
    def post(self):
        """Create a Single {{ capitalize(name) }}"""

        return {{ capitalize(name) }}Service.create(request.parsed_obj)


@api.route("/<int:{{ lower(name) }}Id>")
@api.param("{{ lower(name) }}Id", "{{ capitalize(name) }} database ID")
class {{ capitalize(name) }}IdResource(Resource):
    @responds(schema={{ capitalize(name) }}Schema)
    def get(self, {{ lower(name) }}Id: int) -> {{ capitalize(name) }}:
        """Get Single {{ capitalize(name) }}"""

        return {{ capitalize(name) }}Service.get_by_id({{ lower(name) }}Id)

    def delete(self, {{ lower(name) }}Id: int) -> Response:
        """Delete Single {{ capitalize(name) }}"""

        from flask import jsonify

        id = {{ capitalize(name) }}Service.delete_by_id({{ lower(name) }}Id)
        return jsonify(dict(status="Success", id=id))

    @accepts(schema={{ capitalize(name) }}Schema, api=api)
    @responds(schema={{ capitalize(name) }}Schema)
    def put(self, {{ lower(name) }}Id: int) -> {{ capitalize(name) }}:
        """Update Single {{ capitalize(name) }}"""

        changes = request.parsed_obj
        {{ lower(name) }} = {{ capitalize(name) }}Service.get_by_id({{ lower(name) }}Id)
        return {{ capitalize(name) }}Service.update({{ lower(name) }}, changes)
