
from policy_adherence.common.open_api import JSONSchemaTypes, Schema
import policy_adherence.dmn.dmn as dmn

def convert_json_type_to_dmn(json_type):
    mapping = {
        JSONSchemaTypes.string: "string",
        JSONSchemaTypes.integer: "integer",
        JSONSchemaTypes.number: "double",
        JSONSchemaTypes.boolean: "boolean",
        JSONSchemaTypes.array: "list"
    }
    return mapping.get(json_type, "Any")

def map_schema(name:str, schema:Schema)->dmn.ItemDefinition:
    item = dmn.ItemDefinition(name=name, id=name )

    if schema.type:
        if schema.type == JSONSchemaTypes.object:
            for prop, prop_schema in schema.properties.items() or {}:
                child = map_schema(prop, prop_schema)
                item.itemComponent.append(child)
        elif schema.type == JSONSchemaTypes.array:
            item.isCollection = True
            if schema.items:
                item.typeRef = convert_json_type_to_dmn(schema.items.type)
        else:
            item.typeRef = convert_json_type_to_dmn(schema.type)

    return item

user_schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "first_name": { "type": "string" },
        "last_name": { "type": "string" },
        "age": { "type": "integer" },
        "email": { "type": "string" },
        "address": {
            "type": "object",
            "properties": {
                "city": { "type": "string" },
                "zip": { "type": "string" }
            }
        }
    }
})

def main():
    defs = dmn.Definitions(
            name= "ExampleModel",
            id= "example",
            namespace= "http://example.com/dmn"
        )
    defs.itemDefinition.append(map_schema('User', user_schema))
    defs.inputs.append(dmn.InputData(name="User", id="inUser",
        variable=dmn.InformationItem(typeRef="User", name="User")
    ))
    defs.decisions.append(dmn.Decision(
        name="young",
        decisionLogic=dmn.LiteralExpression(text="User.age &lt;= 18"),
        informationRequirement=[
            dmn.InformationRequirement(
                requiredInput=dmn.DMNRef(href="#inUser"))
        ],
        variable=dmn.InformationItem(name="is_young", typeRef="boolean")))
    
    defs.save("converted_model.dmn")

    print("DMN model saved to 'converted_model.dmn'")

main()