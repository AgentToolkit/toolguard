from typing import List, Optional, Union
from pydantic_xml import BaseXmlModel, attr, element

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
    # expressionLanguage: Optional[str] = attr(default="https://www.omg.org/spec/DMN/20240513/FEEL/")
    # typeLanguage: Optional[str] = attr(default="https://www.omg.org/spec/DMN/20240513/FEEL/")
    itemDefinition: List[ItemDefinition] = element(default=[])
    decisions: List[Decision] = element(default=[])
    inputs: List[InputData] = element(default=[])
    # businessContextElement: List[BusinessContextElement]

    # class Config:
    #     xml_ns = ''  # default namespace (no prefix)
    #     xml_ns_url = "https://www.omg.org/spec/DMN/20191111/MODEL/" 

    def save(self, filename:str):
        with open(filename, "w") as f:
            dmn_xml = self.to_xml(
                pretty_print=True,
                encoding='UTF-8',
                standalone=True,
                # exclude_unset = True,
                exclude_none=True
            )
            f.write(dmn_xml.decode('utf-8'))