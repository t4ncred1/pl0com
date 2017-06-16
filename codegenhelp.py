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
  return '%r'+`regid`
  
  
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

def genSpillLoadIfNecessary(self, var):
  # todo
  return ''
  
  
def getRegisterForVariable(self, var):
  return getRegisterString(self.vartoreg[var])


def genSpillStoreIfNecessary(self, var):
  # todo
  return ''


RegisterAllocation.genSpillLoadIfNecessary = genSpillLoadIfNecessary
RegisterAllocation.getRegisterForVariable = getRegisterForVariable
RegisterAllocation.genSpillStoreIfNecessary = genSpillStoreIfNecessary

