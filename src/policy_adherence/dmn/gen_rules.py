
import os
from os.path import join
from typing import List

from policy_adherence.common.open_api import OpenAPI, RequestBody, JSchema
from policy_adherence.common.str import to_snake_case
from policy_adherence.dmn import dmn
from policy_adherence.dmn.prompt import improve_tool_rules
from policy_adherence.types import SourceFile, ToolPolicy

async def generate_tools_check_rules(app_name:str, tools:List[ToolPolicy], out_folder:str, op_only_oas:OpenAPI):
    app_root = join(out_folder, app_name)
    os.makedirs(app_root, exist_ok=True)

    results = []
    tools_w_poilicies = [tool for tool in tools if len(tool.policy_items) > 0]
    for tool in tools_w_poilicies:
        for tool_item in tool.policy_items:
            
            op = op_only_oas.get_operation_by_operationId("book_reservation")
            assert op
            req_body = op_only_oas.resolve_ref(op.requestBody, RequestBody)
            assert req_body.content_json
            req_schema = op_only_oas.resolve_ref(req_body.content_json.schema_, JSchema)
            assert req_schema
            
            dfs = dmn.Definitions(name=tool_item.name)
            in_def = dmn.map_schema("request", req_schema, op_only_oas)
            dfs.itemDefinition.append(in_def)
            dfs.inputs.append(
                dmn.InputData(name="req", id="req",
                    variable=dmn.InformationItem(typeRef="request", name="request")
                ))
            dfs.decisions.append(dmn.Decision(
                name=tool_item.name,
                decisionLogic=dmn.LiteralExpression(text="FIXME"),
                informationRequirement=[
                    dmn.InformationRequirement(
                        requiredInput=dmn.DMNRef(href="#req"))
                ],
                variable=dmn.InformationItem(name=f"{tool_item.name}_res", typeRef="boolean")))
    
            dfs_src = SourceFile(
                file_name=f"{to_snake_case(tool_item.name)}.xml",
                content=str(dfs)
            )
            dfs_src.save(app_root)
            
            rules_content = improve_tool_rules(dfs_src, tool_item, [])
            print(rules_content)
            res = SourceFile(file_name=dfs_src.file_name+"1", content=rules_content)
            res.save(app_root)
            # results.append(res)

    return results