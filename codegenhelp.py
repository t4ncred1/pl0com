#!/usr/bin/python

from regalloc import *
from datalayout import *


def generateCode(program, regalloc): 
  return program.codegen(regalloc)



