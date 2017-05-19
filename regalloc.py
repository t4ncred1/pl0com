#!/usr/bin/python

__doc__='''Minimal support for register allocation'''

from cfg import *


class NotEnoughRegsException(Exception):
  pass


class minimal_register_allocator(object):

  def __init__(self,cfg,nregs):
    self.cfg=cfg
    self.nregs=nregs
    self.allocresult={}
  

  def __call__(self):
    blockq = self.cfg.heads().values()
    i = 0
    while i < len(blockq):
      n = blockq[i].succ()
      nreal = []
      for b in n:
        if not(b in blockq):
          nreal.append(b)    
      blockq += nreal
      
      bbra = bb_register_allocator(blockq[i], self.nregs)
      thisalloc = bbra()
      print "block:", `id(blockq[i])`
      print "varliveness:\n", `bbra.varliveness`
      print "ralloc:\n", `thisalloc`, "\n"
      self.allocresult.update(thisalloc)
      i += 1

    return self.allocresult
    
    
    
class bb_register_allocator(object):

  def __init__(self, bb, nregs, prevralloc=None):
    self.bb = bb
    self.nregs = nregs
  
    self.vartoreg={}
    #inherit registers across bbs
    if prevralloc:
      livein = bb.live_in
      for livevar in livein:
        if prevralloc[livevar]:
          self.vartoreg[livevar] = prevralloc[livevar]
    
    # liveness of a variable on entry to each instruction
    self.varliveness = dict()   # variable -> set
    
    self.allvars = bb.live_in.union(bb.live_out)
    self.allvars = self.allvars.union(bb.gen.union(bb.kill))
    self.allvars = removeNonRegs(self.allvars)
    self.allvars = list(self.allvars)
    
    
  def computeLivenessIntervalsForVar(self, var):
    liveiset = []
    on = False
    i = len(self.bb.instrs) - 1
    while i >= 0:
      inst = self.bb.instrs[i]
      if var in inst.collect_kills():
        on = False
      if var in inst.collect_uses():
        on = True
      if on:
        liveiset.append(i)
      i -= 1
    self.varliveness[var] = set(liveiset)
    
    
  def testInterference(self, var1, var2):
    li1 = self.varliveness[var1]
    li2 = self.varliveness[var2]
    inters = li1 & li2
    return len(inters) > 0
    
    
  def __call__(self):
    for i in range(0, len(self.allvars)):
      var = self.allvars[i]
      self.computeLivenessIntervalsForVar(var)
      
      freeregs = set(range(0, self.nregs))
      for j in range(0, i):
        var2 = self.allvars[j]
        if self.testInterference(var, var2):
          freeregs.discard(self.vartoreg[var2])
      
      if len(freeregs) == 0:
        print "varliveness:\n", `self.varliveness`
        print "ralloc:\n", `self.vartoreg`
        raise Exception, "spill! " + `var`
      self.vartoreg[var] = freeregs.pop()
      
    return self.vartoreg

      
    
  
      

