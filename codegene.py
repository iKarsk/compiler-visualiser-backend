import llvmlite.ir as ir
import llvmlite.binding as llvm
from ctypes import CFUNCTYPE
import json
import sys
from ASTnodes import (
    ASTnode,
    RootNode,
    TypeNode,
    IntLiteral,
    FloatLiteral,
    BoolLiteral,
    ParamASTnode,
    FunctionDeclarationASTnode,
    CompoundStatement,
    VariableDeclarationNode,
    IfNode,
    WhileNode,
    ForNode,
    ReturnNode,
    BreakNode,
    ContinueNode,
    AssignNode,
    BinaryOperatorNode,
    UnaryOperatorNode,
    FunctionCallNode,
    IdentifierNode
)


def create_ast_node(json_data) -> ASTnode:
    node_type = json_data['node']

    if node_type == 'RootNode':
        declarations = [create_ast_node(declaration) for declaration in json_data['DeclarationList']]
        return RootNode(declarations)
    elif node_type == 'TypeNode':
        return TypeNode(json_data['type'])
    elif node_type == 'IntLiteral':
        return IntLiteral(json_data['value'])
    elif node_type == 'FloatLiteral':
        return FloatLiteral(json_data['value'])
    elif node_type == 'BoolLiteral':
        return BoolLiteral(json_data['value'])
    elif node_type == 'Param':
        type_node = create_ast_node(json_data['type'])
        return ParamASTnode(type_node, json_data['id'])
    elif node_type == 'FunctionDeclaration':
        type_node = create_ast_node(json_data['type'])
        params = [create_ast_node(param) for param in json_data['params']]
        block = create_ast_node(json_data['block'])
        return FunctionDeclarationASTnode(type_node, json_data['id'], params, block)
    elif node_type == 'CompoundStatement':
        declarations = [create_ast_node(declaration) for declaration in json_data['declarations']]
        statements = [create_ast_node(statement) for statement in json_data['statements']]
        return CompoundStatement(declarations, statements)
    elif node_type == 'VariableDeclaration':
        type_node = create_ast_node(json_data['type'])
        initializer = create_ast_node(json_data['initializer']) if json_data['initializer'] is not None else None
        isGlobal = json_data['isGlobal']
        return VariableDeclarationNode(type_node, json_data['id'], isGlobal, initializer)
    elif node_type == 'IfNode':
        condition = create_ast_node(json_data['condition'])
        if_block = create_ast_node(json_data['ifBlock'])
        else_block = create_ast_node(json_data['elseBlock']) if json_data['elseBlock'] is not None else None
        return IfNode(condition, if_block, else_block)

    elif node_type == 'WhileNode':
        condition = create_ast_node(json_data['condition'])
        block = create_ast_node(json_data['block'])
        return WhileNode(condition, block)
    elif node_type == 'ForNode':
        init = create_ast_node(json_data['init'])
        condition = create_ast_node(json_data['condition'])
        increment = create_ast_node(json_data['increment'])
        block = create_ast_node(json_data['block'])
        return ForNode(init, condition, increment, block)
    elif node_type == 'ReturnNode':
        expression = create_ast_node(json_data['expression']) if json_data['expression'] is not None else None
        return ReturnNode(expression)
    elif node_type == 'BreakNode':
        return BreakNode()
    elif node_type == 'ContinueNode':
        return ContinueNode()
    elif node_type == 'AssignNode':
        value = create_ast_node(json_data['value'])
        return AssignNode(json_data['id'], value)
    elif node_type == 'BinaryOperatorNode':
        left = create_ast_node(json_data['left'])
        op = json_data['op']
        right = create_ast_node(json_data['right'])
        return BinaryOperatorNode(left, op, right)
    elif node_type == 'UnaryOperatorNode':
        op = json_data['op']
        right = create_ast_node(json_data['right'])
        return UnaryOperatorNode(op, right)
    elif node_type == 'FunctionCallNode':
        args = [create_ast_node(arg) for arg in json_data['args']]
        return FunctionCallNode(json_data['id'], args)
    elif node_type == 'IdentifierNode':
        return IdentifierNode(json_data['id'])
    else:
        raise ValueError(f"Unsupported node type: {node_type}")


filename = sys.argv[1]
with open('./userCode/' + filename + '.json') as f:
    data = json.load(f)

ProgramAST = create_ast_node(data)

llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()
module = ir.Module(name="custom_module")
# Define a list of dictionaries to represent NamedValues
NamedValues = []

# Define a dictionary to represent GlobalNamedValues
GlobalNamedValues = {}

# Return type of function currently being generated
returnType = [None]

# Whether the function is a new function
newFunction = [False]

builder = ir.IRBuilder()
ProgramAST.codegen(NamedValues, GlobalNamedValues, newFunction, returnType, module, builder)

# print(module)

with open('./userCode/' + filename + ".ll", "w") as f:
    f.write(str(module))


# Create ll file with predefined print function. Previous .ll file is for returning the pure IR code

module = ir.Module(name="custom_module")
# Define a list of dictionaries to represent NamedValues
NamedValues = []

# Define a dictionary to represent GlobalNamedValues
GlobalNamedValues = {}

# Return type of function currently being generated
returnType = [None]

# Whether the function is a new function
newFunction = [False]

func_ty = ir.FunctionType(ir.VoidType(), [ir.IntType(32)])
i32_ty = ir.IntType(32)
func = ir.Function(module, func_ty, name="print")

voidptr_ty = ir.IntType(8).as_pointer()

# fmt = "Hello, %s! %i times!\n\0"
fmt = "%d\n\0"
c_fmt = ir.Constant(ir.ArrayType(ir.IntType(8), len(fmt)),
                    bytearray(fmt.encode("utf8")))
global_fmt = ir.GlobalVariable(module, c_fmt.type, name="fstr")
global_fmt.linkage = 'internal'
global_fmt.global_constant = True
global_fmt.initializer = c_fmt

printf_ty = ir.FunctionType(ir.IntType(32), [voidptr_ty], var_arg=True)
printf = ir.Function(module, printf_ty, name="printf")

builder = ir.IRBuilder(func.append_basic_block('entry'))


# this val can come from anywhere
int_val = func.args[0]

fmt_arg = builder.bitcast(global_fmt, voidptr_ty)
builder.call(printf, [fmt_arg, int_val])

builder.ret_void()


builder = ir.IRBuilder()
ProgramAST.codegen(NamedValues, GlobalNamedValues, newFunction, returnType, module, builder)

print(module)

with open('./userCode/' + filename + "withPrint" + ".ll", "w") as f:
    f.write(str(module))









