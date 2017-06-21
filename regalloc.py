#!/usr/bin/python

__doc__='''Minimal support for register allocation'''

from cfg import *


SPILL_FLAG = 999


class NotEnoughRegsException(Exception):
  pass


class minimal_register_allocator(object):

  def __init__(self,cfg,nregs):
    self.cfg=cfg
    self.nregs=nregs
    self.allocresult=RegisterAllocation(dict(), 0, self.nregs)

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
    
    
class RegisterAllocation(object):

  def __init__(self, vartoreg, numspill, nregs):
    self.vartoreg = vartoreg
    self.numspill = numspill
    self.nregs = nregs
    self.vartospillframeoffset = dict()
    self.spillregi = 0
    self.spillframeoffseti = 0
    
  def update(self, otherra):
    self.vartoreg.update(otherra.vartoreg)
    self.numspill += otherra.numspill
      
  def spillRoom(self):
    return self.numspill * 4;
    
  # resets the register used for a spill variable when we know that instance
  # of the variable is dead
  # we want to keep alternating between one and the other spill-reserved
  # register so that we don't materialize two spilled variables used in the same
  # instruction to the same register
  def dematerializeSpilledVarIfNecessary(self, var):
    if self.vartoreg[var] >= self.nregs - 2:
      self.vartoreg[var] = SPILL_FLAG
    
  # returns if the variable is spilled
  def materializeSpilledVarIfNecessary(self, var):
    if self.vartoreg[var] != SPILL_FLAG:
      if self.vartoreg[var] >= self.nregs - 2:
        return True;
      return False;
    self.vartoreg[var] = self.spillregi + self.nregs - 2
    self.spillregi = (self.spillregi + 1) % 2
    if not (var in self.vartospillframeoffset):
      self.vartospillframeoffset[var] = self.spillframeoffseti
      self.spillframeoffseti += 4
    return True;
    
  def __repr__(self):
    return 'vartoreg = ' + `self.vartoreg`
    
    
    
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
          raise Exception, "register inheritance not fully implemented"
    
    # liveness of a variable on entry to each instruction
    # in order of start point
    self.varliveness = []   # {var=var, liveness=[indexes]}
    
    self.allvars = bb.live_in.union(bb.live_out)
    self.allvars = self.allvars.union(bb.gen.union(bb.kill))
    self.allvars = removeNonRegs(self.allvars)
    self.allvars = list(self.allvars)
    
    
  def computeLivenessIntervals(self):
    vartolasti = dict()
    livevars = set()
    i = len(self.bb.instrs) - 1
    
    while i >= 0:
      inst = self.bb.instrs[i]
      kills = removeNonRegs(inst.collect_kills())
      uses = removeNonRegs(inst.collect_uses())
      livevars -= kills
      livevars |= uses
      
      for var in kills:
        lasti = vartolasti.get(var)
        if lasti:
          self.varliveness.insert(0, {"var":var, "interv":lasti})
      
      for var in livevars:
        lasti = vartolasti.get(var)
        if lasti is None:
          lasti = []
        lasti.insert(0, i)
        vartolasti[var] = lasti
        
      i -= 1
      
    for var in livevars:
      lasti = vartolasti[var]
      if lasti:
        self.varliveness.insert(0, {"var":var, "interv":lasti})
                  
    
  def __call__(self):
    self.computeLivenessIntervals()
    
    live = []
    freeregs = set(range(0, self.nregs-2))  # -2 for spill room
    numspill = 0
    
    for livei in self.varliveness:
      start = livei["interv"][0]
      
      #expire old intervals
      i = 0
      while i < len(live):
        notlivecandidate = live[i]
        if notlivecandidate["interv"][-1] < start:
          live.pop(i)
          freeregs.add(self.vartoreg[notlivecandidate["var"]])
        i += 1
          
      if len(freeregs) == 0:
        tospill = live[-1]
        # keep the longest interval
        if tospill["interv"][-1] > livei["interv"][-1]:
          # we have to spill "tospill"
          self.vartoreg[livei["var"]] = self.vartoreg[tospill["var"]]
          self.vartoreg[tospill["var"]] = SPILL_FLAG
          live.pop(-1)  # remove spill from active
          live.append(livei)  # add i to active
        else:
          self.vartoreg[livei["var"]] = SPILL_FLAG
        numspill += 1
        
      else:
        self.vartoreg[livei["var"]] = freeregs.pop()
        live.append(livei)
      
      # sort the active intervals by increasing end point
      live.sort(key=lambda li: li['interv'][-1])
      
    return RegisterAllocation(self.vartoreg, numspill, self.nregs)

      
    
  
      

