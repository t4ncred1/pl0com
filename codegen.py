#!/usr/bin/env python3

__doc__ = '''Code generation methods for all low-level nodes in the IR.
Codegen functions return a string, consisting of the assembly code they
correspond to. Alternatively, they can return a list where:
 - the first element is the assembly code
 - the second element is extra assembly code to be appended at the end of
   the code of the function they are contained in
This feature can be used only by IR nodes that are contained in a Block, and
is used for adding constant literals.'''


from regalloc import *
from datalayout import *
from ir import *


localconsti = 0

def newLocalConstLabel():
  global localconsti
  lab = '.const' + repr(localconsti)
  localconsti += 1
  return lab 
  
  
def newLocalConst(val):
  lab = newLocalConstLabel()
  trail = lab + ':\n\t.word ' + val + '\n'
  return lab, trail


def symbol_codegen(self, regalloc):
  if self.allocinfo is None:
    return ""
  if not isinstance(self.allocinfo, LocalSymbolLayout):
    return '\t.comm '+ self.allocinfo.symname + ', ' + repr(self.allocinfo.bsize) + "\n"
  else:
    return '\t.equ ' + self.allocinfo.symname + ', ' + repr(self.allocinfo.fpreloff) + "\n"

Symbol.codegen = symbol_codegen


def irnode_codegen(self, regalloc):
  res = ['\t' + comment("irnode " + repr(id(self)) + ' type ' + repr(type(self))), '']
  if 'children' in dir(self) and len(self.children):
    for node in self.children:
      try: 
        try:
          labl = node.getLabel()
          res[0] += labl.name + ':\n'
        except Exception:
          pass
        res = codegenAppend(res, node.codegen(regalloc))
      except Exception as e: 
        res[0] += "\t" + comment("node " + repr(id(node)) + " did not generate any code")
        res[0] += "\t" + comment("exc: " + repr(e))
  return res
  
IRNode.codegen = irnode_codegen


def block_codegen(self, regalloc):
  res = [comment('block'), '']
  for sym in self.local_symtab:
    res = codegenAppend(res, sym.codegen(regalloc))
    
  if self.parent is None:
    res[0] += '\t.global __pl0_start\n'
    res[0] += "__pl0_start:\n"
    
  res[0] += saveRegs(REGS_CALLEESAVE + [REG_FP, REG_LR])
  res[0] += '\tmov ' + getRegisterString(REG_FP) + ', ' + getRegisterString(REG_SP) + '\n'
  stacksp = self.stackroom + regalloc.spillRoom()
  res[0] += '\tsub ' + getRegisterString(REG_SP) + ', ' + getRegisterString(REG_SP) + ', #' + repr(stacksp) + '\n'
  
  regalloc.enterFunctionBody(self)
  try:
    res = codegenAppend(res, self.body.codegen(regalloc))
  except Exception:
    pass
    
  res[0] += '\tmov ' + getRegisterString(REG_SP) + ', ' + getRegisterString(REG_FP) + '\n'
  res[0] += restoreRegs(REGS_CALLEESAVE + [REG_FP, REG_LR])
  res[0] += '\tbx lr\n'
  
  res[0] = res[0] + res[1]
  res[1] = ''
    
  try:
    res = codegenAppend(res, self.defs.codegen(regalloc))
  except Exception:
    pass
    
  return res[0] + res[1]
  
Block.codegen = block_codegen


def deflist_codegen(self, regalloc):
  return ''.join([child.codegen(regalloc) for child in self.children])
  
DefinitionList.codegen = deflist_codegen


def fun_codegen(self, regalloc):
  res = '\n' + self.symbol.name + ':\n'
  res += self.body.codegen(regalloc)
  return res
  
FunctionDef.codegen = fun_codegen


def binstat_codegen(self, regalloc):
  res = regalloc.genSpillLoadIfNecessary(self.srca)
  res += regalloc.genSpillLoadIfNecessary(self.srcb)
  ra = regalloc.getRegisterForVariable(self.srca)
  rb = regalloc.getRegisterForVariable(self.srcb)
  rd = regalloc.getRegisterForVariable(self.dest)
  param = ra + ', ' + rb
  if self.op == "plus":
    res += '\tadd ' + rd + ', ' + param + '\n'
  elif self.op == "minus":
    res += '\tsub ' + rd + ', ' + param + '\n'
  elif self.op == "times":
    res += '\tmul ' + rd + ', ' + param + '\n'
  elif self.op == "slash":
    res += '\tdiv ' + rd + ', ' + param + '\n'
  elif self.op == "eql":
    res += '\tcmp ' + param + '\n'
    res += '\tmoveq ' + rd + ', #1\n'
    res += '\tmovne ' + rd + ', #0\n'
  elif self.op == "neq":
    res += '\tcmp ' + param + '\n'
    res += '\tmoveq ' + rd + ', #0\n'
    res += '\tmovne ' + rd + ', #1\n'
  elif self.op == "lss":
    res += '\tcmp ' + param + '\n'
    res += '\tmovlt ' + rd + ', #1\n'
    res += '\tmovge ' + rd + ', #0\n'
  elif self.op == "leq":
    res += '\tcmp ' + param + '\n'
    res += '\tmovle ' + rd + ', #1\n'
    res += '\tmovgt ' + rd + ', #0\n'
  elif self.op == "gtr":
    res += '\tcmp ' + param + '\n'
    res += '\tmovgt ' + rd + ', #1\n'
    res += '\tmovle ' + rd + ', #0\n'
  elif self.op == "geq":
    res += '\tcmp ' + param + '\n'
    res += '\tmovge ' + rd + ', #1\n'
    res += '\tmovlt ' + rd + ', #0\n'
  else:
    raise Exception("operation " + repr(self.op) + " unexpected")
  return res + regalloc.genSpillStoreIfNecessary(self.dest)
  
BinStat.codegen = binstat_codegen


def print_codegen(self, regalloc):
  res = regalloc.genSpillLoadIfNecessary(self.src)
  rp = regalloc.getRegisterForVariable(self.src)
  res += saveRegs(REGS_CALLERSAVE)
  res += '\tmov ' + getRegisterString(0) + ', ' + rp + '\n'
  res += '\tbl __print\n'
  res += restoreRegs(REGS_CALLERSAVE)
  return res
  
PrintCommand.codegen = print_codegen


def read_codegen(self, regalloc):
  rd = regalloc.getRegisterForVariable(self.dest)
  
  # punch a hole in the saved registers if one of them is the destination
  # of this "instruction"
  savedregs = list(REGS_CALLERSAVE)
  if regalloc.vartoreg[self.dest] in savedregs:
    savedregs.remove(regalloc.vartoreg[self.dest])
    
  res = saveRegs(savedregs)
  res += '\tbl __read\n'
  res += '\tmov ' + rd + ', ' + getRegisterString(0) +  '\n'
  res += restoreRegs(savedregs)
  res += regalloc.genSpillStoreIfNecessary(self.dest)
  return res
  
ReadCommand.codegen = read_codegen


def branch_codegen(self, regalloc):
  targetl = self.target.name
  if not self.returns:
    if self.cond is None:
      return '\tb ' + targetl + '\n'
    else:
      res = regalloc.genSpillLoadIfNecessary(self.cond)
      rcond = regalloc.getRegisterForVariable(self.cond)
      res += '\ttst ' + rcond + ', ' + rcond + '\n'
      return res + '\t' + ('beq' if self.negcond else 'bne') + ' ' + targetl + '\n'
  else:
    if self.cond is None:
      res = saveRegs(REGS_CALLERSAVE)
      res += '\tbl ' + targetl + '\n'
      res += restoreRegs(REGS_CALLERSAVE)
      return res
    else:
      res = regalloc.genSpillLoadIfNecessary(self.cond)
      rcond = regalloc.getRegisterForVariable(self.cond)
      res += '\ttst ' + rcond + ', ' + rcond + '\n'
      res += '\t' + ('bne' if self.negcond else 'beq') + ' ' + rcond + ', 1f\n'
      res += saveRegs(REGS_CALLERSAVE)
      res += '\tbl ' + targetl + '\n'
      res += restoreRegs(REGS_CALLERSAVE)
      res += '1:'
      return res
  return comment('impossible!')
  
BranchStat.codegen = branch_codegen


def emptystat_codegen(self, regalloc):
  return '\t' + comment('emptystat')
  
EmptyStat.codegen = emptystat_codegen


def ldptrto_codegen(self, regalloc):
  rd = regalloc.getRegisterForVariable(self.dest)
  res = ''
  trail = ''
  ai = self.symbol.allocinfo
  if type(ai) is LocalSymbolLayout:
    off = ai.fpreloff
    if off > 0:
      res = '\tadd ' + rd + ', ' + getRegisterString(REG_FP) + ', #' + repr(off) + '\n'
    else:
      res = '\tsub ' + rd + ', ' + getRegisterString(REG_FP) + ', #' + repr(-off) + '\n'
  else:
    lab, tmp = newLocalConst(ai.symname)
    trail += tmp
    res = '\tldr ' + rd + ', ' + lab + '\n'
  return [res + regalloc.genSpillStoreIfNecessary(self.dest), trail]
  
LoadPtrToSym.codegen = ldptrto_codegen


def storestat_codegen(self, regalloc):
  res = ''
  trail = ''
  if self.dest.alloct == 'reg':
    res += regalloc.genSpillLoadIfNecessary(self.dest)
    dest = '[' + regalloc.getRegisterForVariable(self.dest) + ']'
  else:
    ai = self.dest.allocinfo
    if type(ai) is LocalSymbolLayout:
      dest = '[' + getRegisterString(REG_FP) + ', #' + ai.symname + ']'
    else:
      lab, tmp = newLocalConst(ai.symname)
      trail += tmp
      res += '\tldr ' + getRegisterString(REG_SCRATCH) + ', ' + lab + '\n'
      dest = '[' + getRegisterString(REG_SCRATCH) + ']'
      
  if type(self.dest.stype) is PointerType:
    desttype = self.dest.stype.pointstotype
  else:
    desttype = self.dest.stype
  typeid = ['b', 'h', None, ''][desttype.size // 8 - 1]
  if typeid != '' and 'unsigned' in desttype.qual_list:
    typeid = 's' + type
  
  res += regalloc.genSpillLoadIfNecessary(self.symbol)
  rsrc = regalloc.getRegisterForVariable(self.symbol)
  return [res + '\tstr' + typeid + ' ' + rsrc + ', ' + dest + '\n', trail]
  
StoreStat.codegen = storestat_codegen


def loadstat_codegen(self, regalloc):
  res = ''
  trail = ''
  if self.symbol.alloct == 'reg':
    res += regalloc.genSpillLoadIfNecessary(self.symbol)
    src = '[' + regalloc.getRegisterForVariable(self.symbol) + ']'
  else:
    ai = self.symbol.allocinfo
    if type(ai) is LocalSymbolLayout:
      src = '[' + getRegisterString(REG_FP) + ', #' + ai.symname + ']'
    else:
      lab, tmp = newLocalConst(ai.symname)
      trail += tmp
      res += '\tldr ' + getRegisterString(REG_SCRATCH) + ', ' + lab + '\n'
      src = '[' + getRegisterString(REG_SCRATCH) + ']'
      
  if type(self.symbol.stype) is PointerType:
    desttype = self.symbol.stype.pointstotype
  else:
    desttype = self.symbol.stype
  typeid = ['b', 'h', None, ''][desttype.size // 8 - 1]
  if typeid != '' and 'unsigned' in desttype.qual_list:
    typeid = 's' + type
  
  rdst = regalloc.getRegisterForVariable(self.dest)
  res += '\tldr' + typeid + ' ' + rdst + ', ' + src + '\n'
  res += regalloc.genSpillStoreIfNecessary(self.dest)
  return [res, trail]
  
LoadStat.codegen = loadstat_codegen


def loadimm_codegen(self, regalloc):
  rd = regalloc.getRegisterForVariable(self.dest)
  val = self.val
  if val >= -256 and val < 256:
    if val < 0:
      rv = -val - 1
      op = 'mvn '
    else:
      rv = val
      op = 'mov '
    res = '\t' + op + rd + ', #' + repr(rv) + '\n'
    trail = ''
  else:
    lab, trail = newLocalConst(repr(val))
    res = '\tldr ' + rd + ', ' + lab + '\n'
  return [res + regalloc.genSpillStoreIfNecessary(self.dest), trail]
    
LoadImmStat.codegen = loadimm_codegen


def unarystat_codegen(self, regalloc):
  res = regalloc.genSpillLoadIfNecessary(self.src)
  rs = regalloc.getRegisterForVariable(self.src)
  rd = regalloc.getRegisterForVariable(self.dest)
  if self.op == 'plus':
    if rs != rd:
      res += '\tmov ' + rd + ', ' + rs + '\n'
  elif self.op == 'minus':
    res += '\tmvn ' + rd + ', ' + rs + '\n'
    res += '\tadd ' + rd + ', ' + rd + ', #1\n'
  elif self.op == 'odd':
    res += '\tand ' + rd + ', ' + rs + ', #1\n'
  else:
    raise Exception("operation " + repr(self.op) + " unexpected")
  res += regalloc.genSpillStoreIfNecessary(self.dest)
  return res
  
UnaryStat.codegen = unarystat_codegen


def generateCode(program, regalloc):
  res = '\t.text\n'
  res += '\t.arch armv6\n'
  res += '\t.syntax unified\n'
  return res + program.codegen(regalloc)
  



