

from typing import List
from langchain.tools import BaseTool

from .open_api import OpenAPI

def langchain_tools_to_openapi(
    tools: List[BaseTool],
    title: str = "LangChain Tools API",
    version: str = "1.0.0",
)->OpenAPI:
    paths = {}
    components = {"schemas": {}}

    for tool in tools:
        # Get JSON schema from the args model
        if tool.get_input_schema():
            components["schemas"][tool.name + "Args"] = tool.get_input_schema().model_json_schema()

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

        paths[f"/tools/{tool.name}"] = {
            "post": {
                "summary": tool.description,
                "operationId": tool.name,
                "requestBody": request_body,
                "responses": {
                    "200": {
                        "description": "Tool result",
                        "content": {"application/json": tool.get_output_jsonschema()},
                    }
                },
            }
        }

    return OpenAPI.model_validate({
        "openapi": "3.1.0",
        "info": {"title": title, "version": version},
        "paths": paths,
        "components": components,
    })
