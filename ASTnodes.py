from typing import List, Union
import llvmlite.ir as ir
import llvmlite.binding as llvm
import sys

def get_function_named(module, name):
    for func in module.functions:
        if func.name == name:
            return func
    return None

llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

class ParseTree:
    def __init__(self, name: str, children: List['ParseTree'] = None):
        self.name = name
        self.children = children if children is not None else []

class ASTnodeAbstraction:
    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        raise NotImplementedError

class ASTnode(ASTnodeAbstraction):
    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        raise NotImplementedError

class IntLiteral(ASTnode):
    def __init__(self, value: int):
        self.value = value

    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        return ir.Constant(ir.IntType(32), self.value)

class FloatLiteral(ASTnode):
    def __init__(self, value: float):
        self.value = value

    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        return ir.Constant(ir.FloatType(), float(self.value))

class BoolLiteral(ASTnode):
    def __init__(self, value: bool):
        self.value = value

    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        if self.value:
            return ir.Constant(ir.IntType(1), 1)
        else:
            return ir.Constant(ir.IntType(1), 0)
            

class RootNode(ASTnode):
    def __init__(self, DeclarationList: List[ASTnode] = None):
        self.DeclarationList = DeclarationList if DeclarationList is not None else []

    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        for declaration in self.DeclarationList:
            declaration.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder)
        return None

class TypeNode(ASTnode):
    def __init__(self, type: str):
        self.type = type

    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        return None

class ParamASTnode(ASTnode):
    def __init__(self, type: TypeNode, id: str):
        self.type = type
        self.id = id

    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        return None

def string_to_type(string):
    if string.lower() == "int":
        return ir.IntType(32)
    elif string.lower() == "float":
        return ir.FloatType()
    elif string.lower() == "bool":
        return ir.IntType(1)
    else:
        return None

class FunctionDeclarationASTnode(ASTnode):
    def __init__(self, type: TypeNode, id: str, params: List[ParamASTnode], block: 'CompoundStatement'):
        self.type = type
        self.id = id
        self.params = params
        self.block = block

    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        func = get_function_named(module, self.id)

        if func is not None:
            # Function already exists, error
            return None
        
        Args = []

        for param in self.params:
            argType = string_to_type(param.type.type)
            Args.append(argType)

        ReturnType = string_to_type(self.type.type)

        func_ty = ir.FunctionType(ReturnType, Args)
        func = ir.Function(module, func_ty, self.id)

        for i, arg in enumerate(func.args):
            arg.name = str(self.params[i].id)

        bb = func.append_basic_block('entry')
        builder = ir.IRBuilder(bb)

        NamedValues.clear()

        newMap = {}
        newFunction = [True]

        for i, arg in enumerate(func.args):
            alloca = builder.alloca(arg.type, name=arg.name)
            builder.store(arg, alloca)
            newMap[arg.name] = alloca
        
        NamedValues.append(newMap)
        returnType[0] = ReturnType

        # print("\n\n\n")
        # print(ReturnType)
        # print("\n\n\n")

        self.block.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder)

        # print("\n\n\n")
        # print(returnType[0])
        # print("\n\n\n")
        
        if(returnType[0] is not None):
            if(returnType[0] == ir.VoidType()):
                builder.ret_void()
            else:
                builder.ret(ir.Constant(returnType[0], 0))

        return func

class CompoundStatement(ASTnode):
    def __init__(self, declarations: List[ASTnode] = None, statements: List[ASTnode] = None):
        self.declarations = declarations if declarations is not None else []
        self.statements = statements if statements is not None else []

    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        if not newFunction[0]:
            NamedValues.append({})

        newFunction[0] = False

        for declaration in self.declarations:
            declaration.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder)
        
        for statement in self.statements:
            statement.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder)
    
        NamedValues.pop()

        return None

class VariableDeclarationNode(ASTnode):
    def __init__(self, type: TypeNode, id: str, isGlobal: bool, initializer: ASTnode = None):
        self.type = type
        self.id = id
        self.initializer = initializer
        self.isGlobal = isGlobal

    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        if self.isGlobal:
            if self.id in GlobalValues:
                # Error, value already exists
                sys.exit("Semantic Error: " + self.id + " already exists.")
                return None
            
            var_typ = string_to_type(self.type.type)
            V = ir.GlobalVariable(module, var_typ, self.id)
            GlobalValues[self.id] = V

            if self.initializer is None:
                return V

            value = self.initializer.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder)

            if Value.type == var_typ:
                return builder.store(value, V)

            if var_typ == ir.FloatType():
                value = builder.sitofp(value, var_typ, "intToFloat")
            elif var_typ == ir.IntType(32):
                if value.type == ir.IntType(1):
                    value = builder.zext(value, var_typ, "boolToInt")
                else:
                    # Error, cant assign float to int
                    sys.exit("Semantic Error: Attempting to assign float to int")
                    return None
            else:
                # Error, cant assign float or int to bool
                sys.exit("Semantic Error: Attempting to assign float or int to bool")
                return None

            return builder.store(value, V)
            
        else:
            A = NamedValues[-1]

            if self.id in A:
                # Error, value already exists
                sys.exit("Semantic Error: " + self.id + " already exists.")
                return None
            
            var_typ = string_to_type(self.type.type)

            if self.initializer is not None:
                init_val = self.initializer.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder)
            else:
                init_val = None

            saved_block = builder.block
            builder2 = ir.IRBuilder()
            builder2.position_at_start(builder.function.entry_basic_block)
            alloca = builder2.alloca(var_typ, size=None, name=self.id)
            builder.position_at_end(saved_block)

            NamedValues[-1][self.id] = alloca

            if init_val is None:
                return None

            if init_val.type == var_typ:
                return builder.store(init_val, alloca)

            if var_typ == ir.FloatType():
                init_val = builder.sitofp(init_val, var_typ, "intToFloat")
            elif var_typ == ir.IntType(32):
                if init_val.type == ir.IntType(1):
                    init_val = builder.zext(init_val, var_typ, "boolToInt")
                else:
                    # Error, cant assign float to int
                    sys.exit("Semantic Error: attempting to assign float value to integer")
                    return None
            else:
                # Error, cant assign float or int to bool
                sys.exit("Semantic Error: attempting to assign float or integer value to boolean")
                return None

            return builder.store(init_val, V)


class IfNode(ASTnode):
    def __init__(self, condition: ASTnode, ifBlock: ASTnode, elseBlock: ASTnode = None):
        self.condition = condition
        self.ifBlock = ifBlock
        self.elseBlock = elseBlock

    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        condV = self.condition.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder)

        if condV is None:
            # Error
            return None

        if condV.type == ir.IntType(32):
            condV = builder.icmp_signed('!=', condV, ir.Constant(ir.IntType(32), 0))
        elif condV.type == ir.IntType(1):
            condV = builder.icmp_signed('!=', condV, ir.Constant(ir.IntType(1), 0))
        else:
            condV = builder.fcmp_ordered('!=', condV, ir.Constant(ir.FloatType(), 0.0))


        thenBB = builder.function.append_basic_block('then')
        elseBB = ir.Block(builder.function, 'else')
        mergeBB = ir.Block(builder.function, 'merge')

        if self.elseBlock is not None:
            builder.cbranch(condV, thenBB, elseBB)
            builder.position_at_start(thenBB)
            self.ifBlock.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder)

            builder.branch(mergeBB)
            thenBB = builder.block

            builder.function.basic_blocks.append(elseBB)
            builder.position_at_start(elseBB)

            self.elseBlock.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder)

            elseBB = builder.block
            builder.branch(mergeBB)

            builder.function.basic_blocks.append(mergeBB)
            builder.position_at_start(mergeBB)

            return None

        else:

            builder.cbranch(condV, thenBB, mergeBB)
            builder.position_at_start(thenBB)

            self.ifBlock.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder)
            builder.branch(mergeBB)
            thenBB = builder.block

            builder.function.basic_blocks.append(mergeBB)
            builder.position_at_start(mergeBB)

            return None



class WhileNode(ASTnode):
    def __init__(self, condition: ASTnode, block: ASTnode):
        self.condition = condition
        self.block = block

    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        condBB = builder.function.append_basic_block('before')
        whileBB = builder.function.append_basic_block('while')
        mergeBB = ir.Block(builder.function, 'after')

        builder.branch(condBB)
        builder.position_at_start(condBB)

        condV = self.condition.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder)

        if condV is None:
            # Error
            return None

        if condV.type == ir.IntType(32):
            condV = builder.icmp_signed('!=', condV, ir.Constant(ir.IntType(32), 0))
        elif condV.type == ir.IntType(1):
            condV = builder.icmp_signed('!=', condV, ir.Constant(ir.IntType(1), 0))
        else:
            condV = builder.fcmp_ordered('!=', condV, ir.Constant(ir.FloatType(), 0.0))

        builder.cbranch(condV, whileBB, mergeBB)
        builder.position_at_start(whileBB)

        blockV = self.block.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder)

        builder.branch(condBB)
        builder.function.basic_blocks.append(mergeBB)
        builder.position_at_start(mergeBB)

        return None



class ForNode(ASTnode):
    def __init__(self, init: ASTnode, condition: ASTnode, increment: ASTnode, block: ASTnode):
        self.init = init
        self.condition = condition
        self.increment = increment
        self.block = block

    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        startVal = self.init.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder)

        condBB = builder.function.append_basic_block('for.cond')
        bodyBB = builder.function.append_basic_block('for.body')
        afterBB = ir.Block(builder.function, 'for.after')

        builder.branch(condBB)

        builder.position_at_start(condBB)

        condV = self.condition.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder)
        
        if condV is None:
            return None

        if condV.type == ir.IntType(32):
            condV = builder.icmp_signed('!=', condV, ir.Constant(ir.IntType(32), 0))
        elif condV.type == ir.IntType(1):
            condV = builder.icmp_signed('!=', condV, ir.Constant(ir.IntType(1), 0))
        else:
            condV = builder.fcmp_ordered('!=', condV, ir.Constant(ir.FloatType(), 0.0))
        
        builder.cbranch(condV, bodyBB, afterBB)

        builder.position_at_start(bodyBB)
        self.block.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder)

        self.increment.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder)

        builder.branch(condBB)

        builder.function.basic_blocks.append(afterBB)
        builder.position_at_start(afterBB)

        return None

        

class ReturnNode(ASTnode):
    def __init__(self, expression: ASTnode = None):
        self.expression = expression

    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        if self.expression is None and returnType[0] == ir.VoidType():
            returnType[0] = None
            return builder.ret_void()
        
        if self.expression is None and returnType[0] != ir.VoidType():
            # Error, incorrect return type
            sys.exit("Semantic Error: returning incorrect return type")
            return None


        V = self.expression.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder)

        if V.type == returnType[0]:
            returnType[0] = None
            return builder.ret(V)
        
        if returnType[0] == ir.IntType(1) and V.type == ir.IntType(32):
            # Error, returning int from bool
            sys.exit("Semantic Error: returning an integer from a boolean function")
            return None
        elif returnType[0] == ir.IntType(1) and V.type == ir.FloatType():
            sys.exit("Semantic Error: returning a float from a boolean function")
            # Error, returning float from bool func
            return None
        elif returnType[0] == ir.IntType(32) and V.type == ir.FloatType():
            sys.exit("Semantic Error: returning a float from an integer function")
            # Error, returning float from int function
            return None

        if returnType[0] == ir.FloatType():
            V = builder.sitofp(V, returnType[0], "intToFloat")
        elif returnType[0] == ir.IntType(32):
            V = builder.zext(V, returnType[0], "boolToInt")

        returnType[0] = None
        return builder.ret(V)

class BreakNode(ASTnode):
    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        return 'BreakNode()'

class ContinueNode(ASTnode):
    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        return 'ContinueNode()'

class AssignNode(ASTnode):
    def __init__(self, id: str, value: ASTnode):
        self.id = id
        self.value = value

    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        FoundValue = None

        for value in reversed(NamedValues):
            if self.id in value:
                FoundValue = value[self.id]

        if FoundValue is None:
            if self.id in GlobalValues:
                FoundValue = GlobalValues[self.id]

        if FoundValue is None:
            # Error, variable not found
            sys.exit("Semantic Error: variable " + self.id + " cannot be found" )
            return None

        

        V = self.value.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder)
        
        FoundValueType = builder.load(FoundValue).type

        if V.type == FoundValueType:
            return builder.store(V, FoundValue)

        if FoundValueType == ir.FloatType():
            V = builder.sitofp(V, FoundValueType, "intToFloat")
        elif FoundValueType == ir.IntType(32):
            if V.type == ir.IntType(1):
                V = builder.zext(V, FoundValueType, "boolToInt")
            else:
                # Error, cant assign float to int
                sys.exit("Semantic Error: attempting to assign float to integer")
                return None
        else:
            # Error, cant assign float or int to bool
            sys.exit("Semantic Error: attempting to assign float or integer to boolean")
            return None
        
        return builder.store(V, FoundValue)
            

        
        


class BinaryOperatorNode(ASTnode):
    def __init__(self, left: ASTnode, op, right: ASTnode):
        self.left = left
        self.op = op
        self.right = right

    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        VL = self.left.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder)
        VR = self.right.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder)

        if VL is None or VR is None:
            # Error
            return None

        LeftType = VL.type
        RightType = VR.type
        WidestType = VL

        if LeftType == ir.FloatType() or RightType == ir.FloatType():
            WidestType = ir.FloatType()
        elif LeftType == ir.IntType(32) or RightType == ir.IntType(32):
            WidestType = ir.IntType(32)
        else:
            WidestType = ir.IntType(1)

        if LeftType != WidestType:
            if LeftType == ir.IntType(1) and WidestType == ir.IntType(32):
                VL = builder.zext(VL, WidestType, "boolToInt")
            elif LeftType == ir.IntType(1) and WidestType == ir.FloatType():
                VL = builder.sitofp(VL, WidestType, "boolToFloat")
            elif LeftType == ir.IntType(32) and WidestType == ir.FloatType():
                VL = builder.sitofp(VL, WidestType, "intoToFloat")

        if RightType != WidestType:
            if RightType == ir.IntType(1) and WidestType == ir.IntType(32):
                VR = builder.zext(VR, WidestType, "boolToInt")
            elif RightType == ir.IntType(1) and WidestType == ir.FloatType():
                VR = builder.sitofp(VR, WidestType, "boolToFloat")
            elif RightType == ir.IntType(32) and WidestType == ir.FloatType():
                VR = builder.sitofp(VR, WidestType, "intoToFloat")

        LeftType = VL.type
        RightType = VR.type

        if self.op == "+":
            if WidestType == ir.IntType(32) or WidestType == ir.IntType(1):
                return builder.add(VL, VR, "addtmp")
            else:
                return builder.fadd(VL, VR, "addtmp")
        elif self.op == "-":
            if WidestType == ir.IntType(32) or WidestType == ir.IntType(1):
                return builder.sub(VL, VR, "addtmp")
            else:
                return builder.fsub(VL, VR, "addtmp")
        elif self.op == "*":
            if WidestType == ir.IntType(32) or WidestType == ir.IntType(1):
                return builder.mul(VL, VR, "addtmp")
            else:
                return builder.fmul(VL, VR, "addtmp")
        elif self.op == "/":
            if WidestType == ir.IntType(32) or WidestType == ir.IntType(1):
                return builder.sdiv(VL, VR, "addtmp")
            else:
                return builder.fdiv(VL, VR, "addtmp")
        elif self.op == "%":
            if WidestType == ir.IntType(32) or WidestType == ir.IntType(1):
                return builder.srem(VL, VR, "addtmp")
            else:
                return builder.frem(VL, VR, "addtmp")
        elif self.op == "<":
            if WidestType == ir.IntType(32) or WidestType == ir.IntType(1):
                return builder.icmp_signed('<', VL, VR, "addtmp")
            else:
                return builder.fcmp_ordered('<', VL, VR, "addtmp")
        elif self.op == ">":
            if WidestType == ir.IntType(32) or WidestType == ir.IntType(1):
                return builder.icmp_signed('>', VL, VR, "addtmp")
            else:
                return builder.fcmp_ordered('>', VL, VR, "addtmp")
        elif self.op == "<=":
            if WidestType == ir.IntType(32) or WidestType == ir.IntType(1):
                return builder.icmp_signed('<=', VL, VR, "addtmp")
            else:
                return builder.fcmp_ordered('<=', VL, VR, "addtmp")
        elif self.op == ">=":
            if WidestType == ir.IntType(32) or WidestType == ir.IntType(1):
                return builder.icmp_signed('>=', VL, VR, "addtmp")
            else:
                return builder.fcmp_ordered('>=', VL, VR, "addtmp")
        elif self.op == "==":
            if WidestType == ir.IntType(32) or WidestType == ir.IntType(1):
                return builder.icmp_signed('==', VL, VR, "addtmp")
            else:
                return builder.fcmp_ordered('==', VL, VR, "addtmp")
        elif self.op == "!=":
            if WidestType == ir.IntType(32) or WidestType == ir.IntType(1):
                return builder.icmp_signed('!=', VL, VR, "addtmp")
            else:
                return builder.fcmp_ordered('!=', VL, VR, "addtmp")
        elif self.op == "&&":
            if WidestType == ir.IntType(32):
                CondVLeft = builder.icmp_signed('!=', VL, ir.Constant(ir.IntType(32), 0))
                CondVRight = builder.icmp_signed('!=', VR, ir.Constant(ir.IntType(32), 0))
            elif WidestType == ir.IntType(1):
                CondVLeft = builder.icmp_signed('!=', VL, ir.Constant(ir.IntType(32), 0))
                CondVRight = builder.icmp_signed('!=', VR, ir.Constant(ir.IntType(1), 0))
            else:
                CondVLeft = builder.fcmp_ordered('!=', VL, ir.Constant(ir.FloatType(), 0.0))
                CondVRight = builder.fcmp_ordered('!=', VR, ir.Constant(ir.FloatType(), 0.0))
            
            if WidestType == ir.FloatType():
                return builder.fcmp_ordered('==', CondVLeft, CondVRight)
            else:
                return builder.icmp_signed('==', CondVLeft, CondVRight)
        elif self.op == "||":
            if WidestType == ir.IntType(32):
                CondVLeft = builder.icmp_signed('!=', VL, ir.Constant(ir.IntType(32), 0))
                CondVRight = builder.icmp_signed('!=', VR, ir.Constant(ir.IntType(32), 0))
                return builder.or_(CondVLeft, CondVRight)
            elif WidestType == ir.IntType(1):
                CondVLeft = builder.icmp_signed('!=', VL, ir.Constant(ir.IntType(32), 0))
                CondVRight = builder.icmp_signed('!=', VR, ir.Constant(ir.IntType(1), 0))
                return builder.or_(CondVLeft, CondVRight)
            else:
                CondVLeft = builder.fcmp_ordered('!=', VL, ir.Constant(ir.FloatType(), 0.0))
                CondVRight = builder.fcmp_ordered('!=', VR, ir.Constant(ir.FloatType(), 0.0))
                return builder.select(builder.or_(CondVLeft, CondVRight), ir.Constant(ir.FloatType(), 1.0), ir.Constant(ir.FloatType(), 0.0))


        


class UnaryOperatorNode(ASTnode):
    def __init__(self, op, right: ASTnode):
        self.op = op
        self.right = right

    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        V = self.right.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder)

        if V is not None:
            if self.op == "-":
                if V.type == ir.IntType(1):
                    temp = builder.zext(V, ir.IntType(32), "BoolToInt")
                    return builder.neg(temp)
                elif V.type == ir.IntType(32):
                    return builder.neg(V)
                else:
                    return builder.fneg(V)
            elif self.op == "!":
                if V.type == ir.IntType(1) or V.type == ir.IntType(32):
                    return builder.not_(V)
                else:
                    # Invalid type
                    # Raise error
                    return None
            else:
                # Invalid op, raise error
                return None

class FunctionCallNode(ASTnode):
    def __init__(self, id: str, args: List[ASTnode] = None):
        self.id = id
        self.args = args if args is not None else []

    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        calleeFunc = get_function_named(module, self.id)
        
        if calleeFunc is None:
            if self.id == "print":
                return None
            # Raise error, unknown function
            sys.exit("Semantic Error: unknown function " + self.id)
            return None

        if len(calleeFunc.args) != len(self.args):
            # Error, too little or too many arguments
            sys.exit("Semantic Error: function call " + self.id + " has an argument number mismatch")
            return None
        
        callArgs = [arg.codegen(NamedValues, GlobalValues, newFunction, returnType, module, builder) for arg in self.args]
        
        return builder.call(calleeFunc, callArgs, 'calltmp')


class IdentifierNode(ASTnode):
    def __init__(self, id: str):
        self.id = id

    def codegen(self, NamedValues, GlobalValues, newFunction, returnType, module, builder):
        for scope in reversed(NamedValues):
            if self.id in scope:
                alloca_inst = scope[self.id]
                return builder.load(alloca_inst, self.id)
        
        
        if self.id in GlobalValues:
            global_variable = GlobalValues[self.id]
            return builder.load(global_variable, self.id)

        # Log error if identifier not found
        error_msg = f"Unknown variable name {self.id}"
        sys.exit("Semantic Error: Unknown variable name " + self.id)
        return error_msg




