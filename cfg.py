#!/usr/bin/python

__doc__ = '''Control Flow Graph implementation
Includes cfg construction and liveness analysis.'''

from support import get_node_list, get_symbol_tables

class BasicBlock(object):
	def __init__(self, next=None, instrs=None, labels=None):
		'''Structure:
		Zero, one (next) or two (next, target_bb) successors
		Keeps information on labels
		'''
		self.next=next
		if instrs :	self.instrs=instrs
		else : self.instrs=[]
		try :	self.target = self.instrs[-1].target
		except Exception : self.target = None
		if labels : self.labels=labels
		else : self.labels = []
		self.target_bb=None
				
		self.live_in  = set([])
		self.live_out = set([])
		self.kill = set([]) # assigned
		self.gen = set([]) # use before assign
		from ir import AssignStat, StoreStat
		for i in instrs :
			uses = set(i.collect_uses())
			uses.difference_update(self.kill)
			self.gen.update(uses)
			if type(i) in [ AssignStat, StoreStat ]:
				self.kill.add(i.symbol)
		# Total number of registers needed
		self.total_vars_used=len(self.gen.union(self.kill))

	def __repr__(self):
		'''Print in graphviz dot format'''
		from string import join
		instrs = `self.labels`+'\\n' if len(self.labels) else ''
		instrs+=join([ `type(i)` for i in self.instrs ],'\\n')
		res=`id(self)`+' [label="BB'+`id(self)`+'{\\n'+instrs+'}"];\n'
		if self.next :
			res+=`id(self)`+' -> '+`id(self.next)`+' [label="'+`self.next.live_in`+'"];\n'
		if self.target_bb : 
			res+=`id(self)`+' -> '+`id(self.target_bb)`+' [style=dashed,label="'+`self.target_bb.live_in`+'"];\n'
		if not ( self.next or self.target_bb ) :
			res+=`id(self)`+' -> '+'exit'+`id(self.getFunction())`+' [label="'+`self.live_out`+'"];\n'
		return res

	def succ(self):
		return [ s for s in [ self.target_bb, self.next ] if s ]

	def liveness_iteration(self):
		'''Compute live_in and live_out approximation
		Returns: check of fixed point'''
		lin=len(self.live_in)
		lout=len(self.live_out)
		if self.next or self.target_bb :
			self.live_out = reduce(lambda x, y : x.union(y), [s.live_in for s in self.succ()],set([]))
		else : # Consider live out all the global vars
			func = self.getFunction()
			if func != 'global' :	self.live_out = set(func.getGlobalSymbols())
		self.live_in = self.gen.union(self.live_out - self.kill)
		return not ( lin==len(self.live_in) and lout==len(self.live_out) )

	def remove_useless_next(self):
		'''Check if unconditional branch, in that case remove next'''
		try :	
			if self.instrs[-1].is_unconditional() :
				self.next=None
		except AttributeError :
			pass

	def getFunction(self):
		return self.instrs[0].getFunction()

def stat_list_to_bb(sl):
	'''Support function for converting AST StatList to BBs'''
	from ir import BranchStat, CallStat
	bbs = []
	newbb = []
	labels = []
	for n in sl.children :
		try : 
			label=n.getLabel()
			if label :
				if len(newbb) : 
					bb = BasicBlock(None,newbb,labels)
					newbb=[]
					if len(bbs) : bbs[-1].next=bb
					bbs.append(bb)
					labels=[label]
				else : labels.append(label)
		except Exception :
			pass
			
		newbb.append(n)
		
		if isinstance(n,BranchStat) or isinstance(n,CallStat) :
			bb = BasicBlock(None,newbb,labels)
			newbb=[]
			if len(bbs) : bbs[-1].next=bb
			bbs.append(bb)
			labels=[]

	if len(newbb) or len(labels) :
		bb = BasicBlock(None,newbb,labels)
		if len(bbs) : bbs[-1].next=bb
		bbs.append(bb)
	return bbs


class CFG(list):
	'''Control Flow Graph representation'''
	def __init__(self, root):
		from ir import StatList, LabelType
		stat_lists = [ n for n in get_node_list(root) if isinstance(n,StatList) ]
		self += sum([ stat_list_to_bb(sl) for sl in stat_lists ],[])
		for bb in self :
			if bb.target :
				bb.target_bb=self.find_target_bb(bb.target)
			bb.remove_useless_next()

	def heads(self):
		'''Get bbs that are only reached via function call or global entry point'''
		defs=[]
		for bb1 in self :
			head = True
			for bb2 in self :
				if bb2.next==bb1 or bb2.target_bb==bb1 :
					head=False
					break
			if head : defs.append(bb1)	
		from ir import FunctionDef
		res={}
		for bb in defs :
			first = bb.instrs[0]
			parent=first.parent
			while parent and type(parent)!=FunctionDef :
				parent=parent.parent
			if not parent :
				res['global']=bb
			else :
				res[parent]=bb
		return res

	def print_cfg_to_dot(self,filename):
		'''Print the CFG in graphviz dot to file'''
		f=open(filename,"w")
		f.write("digraph G {\n")
		for n in self : f.write(`n`)
		h =self.heads()
		for p in h:
			bb=h[p]
			if p=='global' :
				f.write('main [shape=box];\n')
				f.write('main -> '+`id(bb)`+' [label="'+`bb.live_in`+'"];\n')
			else :
				f.write(p.symbol.name+' [shape=box];\n')
				f.write(p.symbol.name+' -> '+`id(bb)`+' [label="'+`bb.live_in`+'"];\n')
		f.write("}\n")
		f.close()
	
	def print_liveness(self):
		print 'Liveness sets'
		for bb in self :
			print bb
			print 'gen:', bb.gen
			print 'kill:', bb.kill
			print 'live_in:', bb.live_in
			print 'live_out:', bb.live_out

	def find_target_bb(self, label):
		'''Return the BB that contains a given label;
		Support function for creating/exploring the CFG'''
		for bb in self :
			if label in bb.labels :
				return bb
		raise Exception, `label`+' not found in any BB!'

	def liveness(self):
		'''Standard live variable analysis'''
		out = []
		for bb in self :
			out.append(bb.liveness_iteration())
		while sum(out)!=False :
			out=[]
			for bb in self :
				out.append(bb.liveness_iteration())
		return	
