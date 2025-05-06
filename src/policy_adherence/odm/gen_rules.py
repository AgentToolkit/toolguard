
import os
from os.path import join
from typing import List
import uuid


from policy_adherence.common.open_api import OpenAPI, RequestBody, JSchema
from policy_adherence.odm.prompt import improve_tool_rules
from policy_adherence.data_types import SourceFile, ToolPolicy
DOMAIN_PY = "domain.py"

async def generate_tools_check_rules(app_name:str, tools:List[ToolPolicy], out_folder:str, op_only_oas:OpenAPI):
    app_root = join(out_folder, app_name)
    os.makedirs(app_root, exist_ok=True)

    # domain
    # domain = OpenAPICodeGenerator(app_root)\
    #     .generate_domain(openapi_path, DOMAIN_PY)
    
    results = []
    tools_w_poilicies = [tool for tool in tools if len(tool.policy_items) > 0]
    for tool in tools_w_poilicies:
        for tool_item in tool.policy_items:
            
            op = op_only_oas.get_operation_by_operationId("book_reservation")
            assert op
            req_body = op_only_oas.resolve_ref(op.requestBody, RequestBody)
            assert req_body.content_json
            req_schema = op_only_oas.resolve_ref(req_body.content_json.schema_, JSchema)
            bom_src = SourceFile(
                file_name=f"DataModel/schemas/my_project/datamodel/CreateReservation.schema.json",
                content=str(req_schema))
            bom_src.save(app_root)
            
            ruleset_src = SourceFile(
                file_name=f"{tool_item.name}.dmo",
                content=f"""
<ruleset xmlns="http://www.ibm.com/spec/ODM/dmn.xsd" conflictResolution="sequence">
    <input bomType="my_project.datamodel.CreateReservation" collection="false" name="request"/>
    <output bomType="java.lang.Boolean" collection="false" name="{tool_item.name}"/>
    <rule defaultRule="false" href="node_1/{tool_item.name}.drl" kind="BusinessRule" name="{tool_item.name}"/>
</ruleset>""")
            ruleset_src.save(app_root)

            rule_src = SourceFile(
                file_name=f"node_1/{tool_item.name}.drl",
                content=f"""<?xml version="1.0" encoding="UTF-8"?>
<ilog.rules.studio.model.brl:ActionRule xmi:version="2.0" xmlns:xmi="http://www.omg.org/XMI" xmlns:ilog.rules.studio.model.brl="http://ilog.rules.studio/model/brl.ecore">
  <name>{tool_item.name}</name>
  <uuid>{uuid.uuid4()}</uuid>
  <locale>en_US</locale>
  <definition><![CDATA[]]></definition>
</ilog.rules.studio.model.brl:ActionRule>
""")    
            rule_src.save(app_root)
            
            
            rules_content = improve_tool_rules(rule_src, ruleset_src, bom_src , tool_item, [])
            print(rules_content)
            res = SourceFile(file_name=rule_src.file_name, content=rules_content)
            res.save(app_root)
            results.append(res)

    return results