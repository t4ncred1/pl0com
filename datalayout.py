#!/usr/bin/python

__doc__ = '''Data layout computation pass. Each symbol whose location (alloct)
is not a register, is allocated in the local stack frame (LocalSymbol) or in
the data section of the executable (GlobalSymbol).'''


from ir import *


class SymbolLayout(object):
  def __init__(self, symname, bsize):
    self.symname = symname
    self.bsize = bsize
    

class LocalSymbolLayout(SymbolLayout):
  def __init__(self, symname, fpreloff, bsize):
    self.symname = symname
    self.fpreloff = fpreloff
    self.bsize = bsize
    
  def __repr__(self):
    return self.symname + ": fp + (" + `self.fpreloff` + ") [def byte " + \
           `self.bsize` + "]"
    

class GlobalSymbolLayout(SymbolLayout):
  def __init__(self, symname, bsize):
    self.symname = symname
    self.bsize = bsize
    
  def __repr__(self):
    return self.symname + ": def byte " + `self.bsize`
    
    
def performDataLayout(root):
  performDataLayoutOfProgram(root)
  for defin in root.defs.children:
    performDataLayoutOfFunction(defin)

  
def performDataLayoutOfFunction(funcroot):
  offs = 0  # prev fp
  prefix = "_l_" + funcroot.symbol.name + "_"
  for var in funcroot.body.local_symtab:
    if var.stype.size == 0:
      continue
    bsize = var.stype.size / 8
    offs -= bsize
    var.setAllocInfo(LocalSymbolLayout(prefix + var.name, offs, bsize))
  funcroot.body.stackroom = -offs


def performDataLayoutOfProgram(root):
  prefix = "_g_"
  for var in root.local_symtab:
    if var.stype.size == 0:
      continue
    var.setAllocInfo(GlobalSymbolLayout(prefix + var.name, var.stype.size / 8))


