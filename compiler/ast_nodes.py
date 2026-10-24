from dataclasses import dataclass, field


@dataclass
class Program:
    statements: list


@dataclass
class Block:
    statements: list


@dataclass
class Import:
    path: str


@dataclass
class Declaration:
    name: str
    value: object
    immutable: bool
    type_name: str = None


@dataclass
class Assignment:
    name: str
    value: object


@dataclass
class Output:
    value: object


@dataclass
class Input:
    name: str


@dataclass
class Conditional:
    condition: object
    then_block: Block
    else_branch: object = None


@dataclass
class Loop:
    count: object
    body: Block


@dataclass
class Function:
    name: str
    parameters: list
    body: Block


@dataclass
class Return:
    value: object = None


@dataclass
class Stop:
    pass


@dataclass
class Literal:
    value: object


@dataclass
class Name:
    identifier: str


@dataclass
class Unary:
    operator: str
    operand: object


@dataclass
class Binary:
    left: object
    operator: str
    right: object


@dataclass
class Call:
    name: str
    arguments: list = field(default_factory=list)