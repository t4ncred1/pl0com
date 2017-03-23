#!/usr/bin/python

__doc__='''Minimal support for register allocation'''

class NotEnoughRegsException(Exception):
	pass

class minimal_register_allocator(object):
	def __init__(self,cfg,nregs):
		self.cfg=cfg
		self.nregs=nregs
		self.to_alloc={}
		for bb in self.cfg :
			crossing_vars = bb.live_in.union(bb.live_out) - bb.gen.union(bb.kill)
			accessed_vars = bb.gen.union(bb.kill)
			self.to_alloc[bb] = [ accessed_vars, crossing_vars ]
		
		# Create lists of vars to allocate sorted by interval
		all_vars = [ self.to_alloc[bb][0].union(self.to_alloc[bb][1]) for bb in self.to_alloc ]
		all_vars = reduce(lambda x, y : x.union(y), all_vars, set([]))
		self.vars = { v : None for v in all_vars }
		var_freq = { v : len([ bb for bb in self.to_alloc if v in self.to_alloc[bb][0] or v in self.to_alloc[bb][1] ])  for v in self.vars }
		self.var_freq = sorted(var_freq, key=lambda v : var_freq[v], reverse=True)

	def to_spill(self):
		'''BBs that see more variables than there are registers available'''
		return [ bb for bb in self.to_alloc if len(self.to_alloc[bb][0]) + len(self.to_alloc[bb][1]) > self.nregs ]

	def replace(self, var, reg):
		for bb in self.to_alloc :
			if var in self.to_alloc[bb][0] :
				self.to_alloc[bb][0].remove(var)
				self.to_alloc[bb][0].add(reg)
			if var in self.to_alloc[bb][1] :
				self.to_alloc[bb][1].remove(var)
				self.to_alloc[bb][1].add(reg)
		self.vars[var] = reg 
	
	def used_regs(self):
		return set([ self.vars[v] for v in self.vars ])

	def next_free_reg(self):
		u=self.used_regs()
		for i in range(self.nregs):
			if i not in u :
				return i
		raise NotEnoughRegsException, 'Not enough registers!!!'

	def check_interference(self,reg):
		for bb in to_alloc :
			if reg in self.to_alloc[bb][0] or reg in self.to_alloc[bb][1] :
				return True
		return False

	def get_non_interfering(self,var):
		interfering = set([])
		for bb in to_alloc :
			the_vars = self.to_alloc[bb][0].union(self.to_alloc[bb][1])
			if var in the_vars :
				interfering.update(the_vars)
		return set(range(self.nregs)) - interfering

	def __call__(self):
		to_spill=self.to_spill()
		if len(to_spill) :
			print to_spill
			raise Exception, 'Spill has not been performed!'
		while len(self.var_freq): # in order of frequency 
			v = self.var_freq.pop(0)
			if not self.vars[v] :
				try :
					self.replace(v,self.next_free_reg())
				except NotEnoughRegsException :
					candidate_regs = self.get_non_interfering(v)
					if len(candidate_regs) :
						self.replace(v,candidate_regs[0])
					else :
						print self.vars
						raise Exception, 'A spill is needed'
		return self.vars
