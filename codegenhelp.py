#!/usr/bin/python

from regalloc import *
from datalayout import *


def generateCode(program, regalloc): 
  return program.codegen(regalloc)


def getRegisterString(regid):
  return '%r'+`regid`
  
  
def spillLoadIfNecessary(var, regalloc):
  # todo
  return ''
  
  
def getRegisterForVariable(var, regalloc):
  return getRegisterString(regalloc.vartoreg[var])


def spillStoreIfNecessary(var, regalloc):
  # todo
  return ''

