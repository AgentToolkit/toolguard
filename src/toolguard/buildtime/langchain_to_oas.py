from typing import Any, Dict, List
from langchain_core.tools import BaseTool

from .utils.dict import substitute_refs
from .utils.open_api import OpenAPI


def langchain_tools_to_openapi(
    tools: List[BaseTool],
    title: str = "LangChain Tools API",
    version: str = "1.0.0",
) -> OpenAPI:
    paths = {}
    components: Dict[str, Dict[str, Any]] = {"schemas": {}}

    for tool in tools:
        # Get JSON schema from the args model
        if tool.get_input_schema():
            components["schemas"][tool.name + "Args"] = (
                tool.get_input_schema().model_json_schema()
            )

            request_body = {
                "description": tool.description,
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{tool.name}Args"}
                    }
                },
            }
        else:
            # Tools without args → empty schema
            request_body = None

        out_schema: Dict = tool.get_output_jsonschema()
        if tool.metadata and tool.metadata.get(
            "output_schema"
        ):  # Langflow metadata.output_schema overrides
            out_schema = tool.metadata.get("output_schema", {})
        out_schema = substitute_refs(out_schema)

        if out_schema.get("x-fastmcp-wrap-result"):  # a 'result' MCP wrapper
            out_schema = out_schema.get("properties", {}).get("result", {})

        paths[f"/tools/{tool.name}"] = {
            "post": {
                "summary": tool.description,
                "operationId": tool.name,
                "requestBody": request_body,
                "responses": {
                    "200": {
                        "description": "Tool result",
                        "content": {"application/json": {"schema": out_schema}},
                    }
                },
            }
        }

    return OpenAPI.model_validate(
        {
            "openapi": "3.1.0",
            "info": {"title": title, "version": version},
            "paths": paths,
            "components": components,
        }
    )
