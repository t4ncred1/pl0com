#!/usr/bin/python

__doc__='''Minimal support for register allocation'''

from cfg import *


class NotEnoughRegsException(Exception):
  pass


class minimal_register_allocator(object):

  def __init__(self,cfg,nregs):
    self.cfg=cfg
    self.nregs=nregs
    self.allocresult=RegisterAllocation(dict(), dict())
  

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

  def __init__(self, vartoreg, spillsets):
    self.vartoreg = vartoreg
    self.spillsets = spillsets  # dict reg -> set(vars allocated to the same reg)
    
  def update(self, otherra):
    self.vartoreg.update(otherra.vartoreg)
    allregs = set(otherra.spillsets.keys()) | set(otherra.spillsets.keys())
    for reg in allregs:
      a = otherra.spillsets.get(reg)
      b = self.spillsets.get(reg)
      if a is None:
        a = set()
      if b is None:
        b = set()
      self.spillsets[reg] = a | b
    
  def __repr__(self):
    return 'vartoreg = ' + `self.vartoreg` + '\nspillsets = ' + `self.spillsets`
    
    
    
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
    spillsets = {}
    freeregs = set(range(0, self.nregs))
    
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
        reg = self.vartoreg[tospill["var"]]
        self.vartoreg[livei["var"]] = reg
        # keep the longest interval
        if tospill["interv"][-1] < livei["interv"][-1]:
          live.pop(-1)
          live.append(livei)
        # add these vars to the spill set for this register so that we can
        # generate the code correctly
        spillset = spillsets.get(reg)
        if spillset is None:
          spillset = set()
        spillset |= set([tospill["var"], livei["var"]])
        spillsets[reg] = spillset
        
      else:
        self.vartoreg[livei["var"]] = freeregs.pop()
        live.append(livei)
      
    return RegisterAllocation(self.vartoreg, spillsets)

      
    
  
      

