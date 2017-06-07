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
  res = "; irnode " + `id(self)` + "\n"
  if 'children' in dir(self) and len(self.children):
    for node in self.children:
      try: 
        res += node.codegen(regalloc)
      except Exception as e: 
        res += "; node " + `id(node)` + " did not generate any code\n"
        res += "; exc: " + `e` + "\n"
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
  res = spillLoadIfNecessary(self.srca, regalloc)
  res += spillLoadIfNecessary(self.srcb, regalloc)
  ra = getRegisterForVariable(self.srca, regalloc)
  rb = getRegisterForVariable(self.srcb, regalloc)
  rd = getRegisterForVariable(self.dest, regalloc)
  param = ra + ', ' + rb + ', ' + rd
  if self.op == "plus":
    res += 'add ' + param + '\n'
  elif self.op == "minus":
    res += 'sub ' + param + '\n'
  elif self.op == "times":
    res += 'mul ' + param + '\n'
  elif self.op == "slash":
    res += 'div ' + param + '\n'
  else:
    raise Exception, "operation " + `self.op` + " unexpected"
  return res + spillStoreIfNecessary(self.dest, regalloc)
  
BinStat.codegen = binstat_codegen


def generateCode(program, regalloc): 
  return program.codegen(regalloc)
  










