import llvmlite.ir as ir
import llvmlite.binding as llvm
from ctypes import CFUNCTYPE
import json
import sys

filename = sys.argv[1]

with open('./userCode/' + filename + "withPrint" + ".ll", "r") as f:
    module = f.read()


llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

llvm_module = llvm.parse_assembly(str(module))
tm = llvm.Target.from_default_triple().create_target_machine()

with llvm.create_mcjit_compiler(llvm_module, tm) as ee:
    ee.finalize_object()
    fptr = ee.get_function_address("main")
    py_func = CFUNCTYPE(ir.IntType(32))(fptr)
    py_func()