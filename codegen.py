#!/usr/bin/python

from regalloc import *
from datalayout import *
from ir import *


def symbol_codegen(self, regalloc):
  if self.allocinfo is None:
    return ""
  if not isinstance(self.allocinfo, LocalSymbolLayout):
    return self.allocinfo.symname + ':\t.space ' + `self.allocinfo.bsize` + "\n"
  else:
    return self.allocinfo.symname + ':\t.equ ' + `self.allocinfo.fpreloff` + "\n"

Symbol.codegen = symbol_codegen


def irnode_codegen(self, regalloc):
  res = "\t; irnode " + `id(self)` + ' type ' + `type(self)` + "\n"
  if 'children' in dir(self) and len(self.children):
    for node in self.children:
      try: 
        try:
          labl = node.getLabel()
          res += labl.name + ':\n'
        except Exception:
          pass
        res += node.codegen(regalloc)
      except Exception as e: 
        res += "\t; node " + `id(node)` + " did not generate any code\n"
        res += "\t; exc: " + `e` + "\n"
  return res
  
IRNode.codegen = irnode_codegen


def block_codegen(self, regalloc):
  res = "; block\n"
  for sym in self.local_symtab:
    res += sym.codegen(regalloc)
    
  if self.parent is None:
    res += "_start:\n"
    
  res += saveRegs(REGS_CALLEESAVE + [REG_FP, REG_LR])
  res += '\tmov ' + getRegisterString(REG_FP) + ', ' + getRegisterString(REG_SP) + '\n'
  stacksp = self.stackroom + regalloc.spillRoom()
  res += '\tsub ' + getRegisterString(REG_SP) + ', ' + getRegisterString(REG_SP) + ', #' + `stacksp` + '\n'
    
  regalloc.enterFunctionBody(self)
  try:
    res += self.body.codegen(regalloc)
  except Exception:
    pass
    
  res += '\tmov ' + getRegisterString(REG_SP) + ', ' + getRegisterString(REG_FP) + '\n'
  res += restoreRegs(REGS_CALLEESAVE + [REG_FP, REG_LR])
  res += '\tbx lr\n'
    
  try:
    res += self.defs.codegen(regalloc)
  except Exception:
    pass
  return res
  
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
    raise Exception, "operation " + `self.op` + " unexpected"
  return res + regalloc.genSpillStoreIfNecessary(self.dest)
  
BinStat.codegen = binstat_codegen


def print_codegen(self, regalloc):
  res = regalloc.genSpillLoadIfNecessary(self.src)
  rp = regalloc.getRegisterForVariable(self.src)
  res += '\tpush ' + getRegisterString(0) + '\n'
  res += '\tmov ' + getRegisterString(0) + ', ' + rp + '\n'
  res += '\tbl __print\n'
  res += '\tpop ' + getRegisterString(0) + '\n'
  return res
  
PrintCommand.codegen = print_codegen


def branch_codegen(self, regalloc):
  targetl = self.target.name
  if not self.returns:
    if self.cond is None:
      return '\tb ' + targetl + '\n'
    else:
      res = regalloc.genSpillLoadIfNecessary(self.cond)
      rcond = regalloc.getRegisterForVariable(self.cond)
      return res + '\tcbnz ' + rcond + ', ' + targetl + '\n'
  else:
    if self.cond is None:
      res = saveRegs(REGS_CALLERSAVE)
      res += '\tbl ' + targetl + '\n'
      res += restoreRegs(REGS_CALLERSAVE)
      return res
    else:
      res = regalloc.genSpillLoadIfNecessary(self.cond)
      rcond = regalloc.getRegisterForVariable(self.cond)
      res += '\tcbz ' + rcond + ', 1f\n'
      res += saveRegs(REGS_CALLERSAVE)
      res += '\tbl ' + targetl + '\n'
      res += restoreRegs(REGS_CALLERSAVE)
      res += '1:'
      return res
  return '\t; impossible!\n'
  
BranchStat.codegen = branch_codegen


def emptystat_codegen(self, regalloc):
  return '\t; emptystat\n'
  
EmptyStat.codegen = emptystat_codegen


def ldptrto_codegen(self, regalloc):
  rd = regalloc.getRegisterForVariable(self.dest)
  res = ''
  ai = self.symbol.allocinfo
  if type(ai) is LocalSymbolLayout:
    off = ai.fpreloff
    if off > 0:
      res = '\tadd ' + rd + ', ' + getRegisterString(REG_FP) + ', #' + `off` + '\n'
    else:
      res = '\tsub ' + rd + ', ' + getRegisterString(REG_FP) + ', #' + `-off` + '\n'
  else:
    res = '\teor ' + rd + ', ' + rd + ', ' + rd + '\n'
    res += '\tadr ' + rd + ', ' + ai.symname + '\n'
  return res + regalloc.genSpillStoreIfNecessary(self.dest)
  
LoadPtrToSym.codegen = ldptrto_codegen


def storestat_codegen(self, regalloc):
  res = ''
  if self.dest.alloct == 'reg':
    res += regalloc.genSpillLoadIfNecessary(self.dest)
    dest = '[' + regalloc.getRegisterForVariable(self.dest) + ']'
  else:
    ai = self.dest.allocinfo
    if type(ai) is LocalSymbolLayout:
      dest = '[' + getRegisterString(REG_FP) + ', #' + ai.symname + ']'
    else:
      dest = ai.symname
      
  typeid = ['b', 'h', None, ''][self.dest.stype.size / 8 - 1]
  if typeid != '' and 'unsigned' in self.dest.stype.qualifiers:
    typeid = 's' + type
  
  res += regalloc.genSpillLoadIfNecessary(self.symbol)
  rsrc = regalloc.getRegisterForVariable(self.symbol)
  return '\tstm' + typeid + ' ' + rsrc + ', ' + dest + '\n'
  
StoreStat.codegen = storestat_codegen


def loadstat_codegen(self, regalloc):
  res = ''
  if self.symbol.alloct == 'reg':
    res += regalloc.genSpillLoadIfNecessary(self.symbol)
    src = '[' + regalloc.getRegisterForVariable(self.symbol) + ']'
  else:
    ai = self.symbol.allocinfo
    if type(ai) is LocalSymbolLayout:
      src = '[' + getRegisterString(REG_FP) + ', #' + ai.symname + ']'
    else:
      src = ai.symname
      
  typeid = ['b', 'h', None, ''][self.symbol.stype.size / 8 - 1]
  if typeid != '' and 'unsigned' in self.symbol.stype.qualifiers:
    typeid = 's' + type
  
  rdst = regalloc.getRegisterForVariable(self.dest)
  res += '\tldm' + typeid + ' ' + rdst + ', ' + src + '\n'
  res += regalloc.genSpillStoreIfNecessary(self.dest)
  return res
  
LoadStat.codegen = loadstat_codegen


def loadimm_codegen(self, regalloc):
  rd = regalloc.getRegisterForVariable(self.dest)
  val = self.val
  if val >= -4096 and val < 4096:
    if val < 0:
      rv = -val - 1
      op = 'mvn '
    else:
      rv = val
      op = 'mov '
    res = '\t' + op + rd + ', #' + `rv` + '\n'
  else:
    bottom = val & 0xffff
    top = val >> 16
    res = '\tmov ' + rd + ', #', `bottom` + '\n'
    res = '\tmovt ' + rd + ', #', `top` + '\n'
  return res + regalloc.genSpillStoreIfNecessary(self.dest)
    
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
    raise Exception, "operation " + `self.op` + " unexpected"
  res += regalloc.genSpillStoreIfNecessary(self.dest)
  return res
  
UnaryStat.codegen = unarystat_codegen


def generateCode(program, regalloc): 
  return program.codegen(regalloc)
  



