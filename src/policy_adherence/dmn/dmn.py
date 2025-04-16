from typing import List, Optional, Union
from pydantic_xml import BaseXmlModel, attr, element
from policy_adherence.common.jschema import JSONSchemaTypes, JSchema
from policy_adherence.common.ref import DocumentWithRef
class DMNElement(BaseXmlModel):
    id: str|None = attr(default=None)
    description: str|None = attr(default=None)
    label: str|None = attr(default=None)

class DMNRef(BaseXmlModel):
    href: str = attr()

class NamedElement(DMNElement):
    name: str = attr()
    
class ItemDefinition(NamedElement):
    typeRef: str|None = element(default=None)
    itemComponent: List['ItemDefinition'] = element(default=[])
    isCollection: bool = attr(default=False)

class DRGElement(NamedElement):
    pass

class Expression(DMNElement):
    typeRef: str|None = element(default=None)

class LiteralExpression(Expression, tag="literalExpression"):
    text: str = element()

class DecisionTable(Expression):
    pass

class Invocation(Expression):
    pass

class InformationRequirement(DMNElement):
    requiredDecision: Optional[DMNRef] = element(default=None)
    requiredInput: Optional[DMNRef] = element(default=None)

class KnowledgeRequirement(DMNElement):
    pass

class AuthorityRequirement(DMNElement):
    pass

class InformationItem(NamedElement):
    typeRef: str|None = attr(default=None)

class InputData(DRGElement, tag="inputData"):
    variable: InformationItem

class Decision(DRGElement, tag="decision"):
    question: str|None = element(default=None)
    allowedAnswers: str|None = element(default=None)
    informationRequirement: List[InformationRequirement] = element(default=[])
    knowledgeRequirement: List[KnowledgeRequirement] = element(default=[])
    authorityRequirement: List[AuthorityRequirement] = element(default=[])
    decisionLogic: Union[LiteralExpression, DecisionTable]| None = element(default=None)
    variable: InformationItem

# class BusinessContextElement

class Definitions(NamedElement, 
        tag="definitions", 
        nsmap={
            "": "https://www.omg.org/spec/DMN/20191111/MODEL/",
            "feel": "http://www.omg.org/spec/FEEL/20140401"
        }):
    namespace: str|None = attr(default=None)
    expressionLanguage: Optional[str] = attr(default="https://www.omg.org/spec/DMN/20240513/FEEL/")
    typeLanguage: Optional[str] = attr(default="https://www.omg.org/spec/DMN/20240513/FEEL/")

    itemDefinition: List[ItemDefinition] = element(default=[])
    decisions: List[Decision] = element(default=[])
    inputs: List[InputData] = element(default=[])
    # businessContextElement: List[BusinessContextElement]

    # class Config:
    #     xml_ns = ''  # default namespace (no prefix)
    #     xml_ns_url = "https://www.omg.org/spec/DMN/20191111/MODEL/" 
    def __str__(self)->str:
        return self.to_xml(
            pretty_print=True,
            encoding='unicode',
            standalone=True,
            # exclude_unset = True,
            exclude_none=True
        )
    def save(self, filename:str):
        with open(filename, "w") as f:
            f.write(str(self))



def convert_json_type_to_dmn(json_type):
    mapping = {
        JSONSchemaTypes.string: "string",
        JSONSchemaTypes.integer: "integer",
        JSONSchemaTypes.number: "double",
        JSONSchemaTypes.boolean: "boolean",
        JSONSchemaTypes.array: "list"
    }
    return mapping.get(json_type, "Any")

def map_schema(name:str, schema:JSchema, doc:DocumentWithRef)->ItemDefinition:
    item = ItemDefinition(name=name, id=name )
    if schema.allOf:
        items = [map_schema(name, doc.resolve_ref(scm, JSchema), doc) for scm in schema.allOf]
        for it in items:
            item.itemComponent.extend(it.itemComponent)

    if schema.type:
        if schema.type == JSONSchemaTypes.object:
            for prop, prop_schema in schema.properties.items() or {}:
                child = map_schema(prop, prop_schema, doc)
                item.itemComponent.append(child)
        elif schema.type == JSONSchemaTypes.array:
            item.isCollection = True
            if schema.items:
                item.typeRef = convert_json_type_to_dmn(schema.items.type)
        else:
            item.typeRef = convert_json_type_to_dmn(schema.type)

    return item