from policy_adherence.common.jschema import JSchema
from policy_adherence.dmn import dmn


user_schema = JSchema.model_validate({
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
    defs.itemDefinition.append(dmn.map_schema('User', user_schema))
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