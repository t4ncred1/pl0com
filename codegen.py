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
  try:
    res += self.body.codegen(regalloc)
  except Exception:
    pass
  return res
  
Block.codegen = block_codegen


def binstat_codegen(self, regalloc):
  res = regalloc.genSpillLoadIfNecessary(self.srca)
  res += regalloc.genSpillLoadIfNecessary(self.srcb)
  ra = regalloc.getRegisterForVariable(self.srca)
  rb = regalloc.getRegisterForVariable(self.srcb)
  rd = regalloc.getRegisterForVariable(self.dest)
  param = ra + ', ' + rb + ', ' + rd
  if self.op == "plus":
    res += '\tadd ' + param + '\n'
  elif self.op == "minus":
    res += '\tsub ' + param + '\n'
  elif self.op == "times":
    res += '\tmul ' + param + '\n'
  elif self.op == "slash":
    res += '\tdiv ' + param + '\n'
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
      return '\tbl ' + targetl + '\n'
    else:
      res = regalloc.genSpillLoadIfNecessary(self.cond)
      rcond = regalloc.getRegisterForVariable(self.cond)
      res += '\tcbz ' + rcond + ', 1f\n'
      res += '\tbl ' + targetl + '\n'
      res += '1:'
      return res
  return '; impossible!\n'
  
BranchStat.codegen = branch_codegen


def generateCode(program, regalloc): 
  return program.codegen(regalloc)
  










