#!/usr/bin/python

from regalloc import *
from datalayout import *


REG_FP = 11
REG_SP = 13
REG_LR = 14
REG_PC = 15

REGS_CALLEESAVE = [4, 5, 6, 7, 8, 9, 10]
REGS_CALLERSAVE = [0, 1, 2, 3]


def getRegisterString(regid):
  if regid == REG_LR:
    return 'lr'
  if regid == REG_SP:
    return 'sp'
  return 'r'+`regid`
  
  
def saveRegs(reglist):
  if len(reglist) == 0:
    return ''
  res = '\tpush {'
  for i in range(0, len(reglist)):
    if i > 0:
      res += ', '
    res += getRegisterString(reglist[i])
  res += '}\n'
  return res
  
  
def restoreRegs(reglist):
  if len(reglist) == 0:
    return ''
  res = '\tpop {'
  for i in range(0, len(reglist)):
    if i > 0:
      res += ', '
    res += getRegisterString(reglist[i])
  res += '}\n'
  return res
  

# class RegisterAllocation:


def enterFunctionBody(self, block):
  self.curfun = block
  self.spillvarloc = dict()
  self.spillvarloctop = -block.stackroom
  

def genSpillLoadIfNecessary(self, var):
  if not self.materializeSpilledVarIfNecessary(var):
    return ''
  offs = self.spillvarloctop - self.vartospillframeoffset[var] - 4
  rd = self.getRegisterForVariable(var)
  res = '\tldm ' + rd + ', [' + getRegisterString(REG_FP) + ', #' + `offs` + ']'
  res += '\t ; <<- fill\n'
  return res
  
  
def getRegisterForVariable(self, var):
  self.materializeSpilledVarIfNecessary(var)
  return getRegisterString(self.vartoreg[var])


def genSpillStoreIfNecessary(self, var):
  if not self.materializeSpilledVarIfNecessary(var):
    return ''
  offs = self.spillvarloctop - self.vartospillframeoffset[var] - 4
  rd = self.getRegisterForVariable(var)
  res = '\tstm ' + rd + ', [' + getRegisterString(REG_FP) + ', #' + `offs` + ']'
  res += '\t ; <<- spill\n'
  return res


RegisterAllocation.enterFunctionBody = enterFunctionBody
RegisterAllocation.genSpillLoadIfNecessary = genSpillLoadIfNecessary
RegisterAllocation.getRegisterForVariable = getRegisterForVariable
RegisterAllocation.genSpillStoreIfNecessary = genSpillStoreIfNecessary

