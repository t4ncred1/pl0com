#!/usr/bin/python

from regalloc import *
from datalayout import *


def getRegisterString(regid):
  return '%r'+`regid`
  

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

