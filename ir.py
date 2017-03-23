#!/usr/bin/python

__doc__='''Intermediate Representation
Could be improved by relying less on class hierarchy and more on string tags and/or duck typing
Includes lowering and flattening functions'''

#SYMBOLS AND TYPES
basetypes = [ 'Int', 'Float', 'Label', 'Struct', 'Function' ]
qualifiers = [ 'unsigned' ]

class Type(object):
	def __init__(self, name, size, basetype, qualifiers=None):
		self.name=name
		self.size=size
		self.basetype=basetype
		self.qual_list=qualifiers

class ArrayType(Type):
	def __init__(self, name, size, basetype):
		self.name=name
		self.size=size
		self.basetype=basetype
		self.qual_list=[]

class StructType(Type):
	def __init__(self, name, size, fields):
		self.name=name
		self.fields=fields
		self.size=self.getSize()
		self.basetype='Struct'
		self.qual_list=[]
		
	def getSize(self):
		return sum([ f.size for f in self.fields])
		
class LabelType(Type):
	def __init__(self):
		self.name='label'
		self.size=0
		self.basetype='Label'
		self.qual_list=[]
		self.ids=0
	
	def __call__(self,target=None):
		self.ids+=1
		return Symbol(name='label'+`self.ids`, stype=self, value=target)

class FunctionType(Type):
	def __init__(self):
		self.name='function'
		self.size=0
		self.basetype='Function'
		self.qual_list=[]

standard_types = {
	'int'  : Type('int',   32, 'Int'),
	'short': Type('short', 16, 'Int'),
	'char' : Type('char',   8, 'Int'),
	'uchar': Type('uchar',  8, 'Int', ['unsigned']),
	'uint' : Type('uint',  32, 'Int', ['unsigned']),
	'ushort': Type('ushort',16,'Int', ['unsigned']),
	'float': Type('float', 32, 'Float'),
	'label': LabelType(),
	'function' : FunctionType(),
}

class Symbol(object):
	def __init__(self, name, stype, value=None):
		self.name=name
		self.stype=stype
		self.value=value # if not None, it is a constant

	def __repr__(self):
		return self.stype.name+' '+self.name + ( self.value if type(self.value)==str else '')

class SymbolTable(list):
	def find(self, name):
		print 'Looking up', name
		for s in self :
			if s.name==name : return s
		print 'Looking up failed!'
		return None

	def __repr__(self):
		res='SymbolTable:\n'
		for s in self :
			res+=repr(s)+'\n'
		return res
		
	def exclude(self, barred_types):
		return [ symb for symb in self if symb.stype not in barred_types ]


#IRNODE
class IRNode(object):
	def __init__(self,parent=None, children=None, symtab=None):
		self.parent=parent
		if children :	self.children=children
		else : self.children=[]
		self.symtab=symtab
	
	def __repr__(self):
		from string import split, join
		attrs = set(['body','cond', 'value','thenpart','elsepart', 'symbol', 'call', 'step', 'expr', 'target', 'defs', 'global_symtab', 'local_symtab' ]) & set(dir(self))

		res=`type(self)`+' '+`id(self)`+' {\n'
		try :
			label=self.getLabel()
			res=label.name+': '+res
		except Exception, e :
			pass
		if 'children' in dir(self) and len(self.children) :
			res+='\tchildren:\n'
			for node in self.children :
				rep=repr(node)
				res+=join([ '\t'+s for s in rep.split('\n') ],'\n')+'\n'
		for d in attrs :
			node=getattr(self,d)
			rep=repr(node)
			res+='\t'+d+': '+join([ '\t'+s for s in rep.split('\n') ],'\n')+'\n'		
		res+='}'
		return res

	def navigate(self, action):
		action(self)
		attrs = set(['body','cond', 'value','thenpart','elsepart', 'symbol', 'call', 'step', 'expr', 'target', 'defs', 'global_symtab', 'local_symtab' ]) & set(dir(self))
		if 'children' in dir(self) and len(self.children) :
			#print 'navigating children of', type(self), id(self), len(self.children)
			for node in self.children :
				try : node.navigate(action)
				except Exception : pass
		for d in attrs :
			try : getattr(self,d).navigate(action)
			except Exception : pass
	
	def replace(self, old, new):
		if 'children' in dir(self) and len(self.children) and old in self.children:
			self.children[self.children.index(old)]=new
			return True
		attrs = set(['body','cond', 'value','thenpart','elsepart', 'symbol', 'call', 'step', 'expr', 'target', 'defs', 'global_symtab', 'local_symtab' ]) & set(dir(self))
		for d in attrs :
			try :
				if getattr(self,d)==old :
					setattr(self,d,new)
					return True			
			except Exception :
				pass
		return False
			

#CONST and VAR	
class Const(IRNode):
	def __init__(self,parent=None, value=0, symb=None, symtab=None):
		self.parent=parent
		self.value=value
		self.symbol=symb
		self.symtab=symtab
		
class Var(IRNode):
	def __init__(self,parent=None, var=None, symtab=None):
		self.parent=parent
		self.symbol=var
		self.symtab=symtab

	def collect_uses(self):
		return [self.symbol]

#EXPRESSIONS
class Expr(IRNode):
	def getOperator(self):
		return self.children[0]

	def collect_uses(self):
		uses = []
		for c in self.children :
			try : uses += c.collect_uses()
			except AttributeError : pass
		return uses

class BinExpr(Expr):
	def getOperands(self):
		return self.children[1:]

class UnExpr(Expr):
	def getOperand(self):
		return self.children[1]

class CallExpr(Expr):
	def __init__(self, parent=None, function=None, parameters=None, symtab=None):
		self.parent=parent
		self.symbol=function
		if parameters : self.children=parameters[:]
		else : self.children=[]

#STATEMENTS
class Stat(IRNode):
	def setLabel(self, label):
		self.label=label
		label.value=self # set target
	
	def getLabel(self):
		return self.label

	def getFunction(self):
		if not self.parent : return 'global'
		elif type(self.parent)== FunctionDef :
			return self.parent
		else :
			return self.parent.getFunction()
			

class CallStat(Stat):	
	'''Procedure call (non returning)'''
	def __init__(self, parent=None, call_expr=None, symtab=None):
		self.parent=parent
		self.call=call_expr
		self.call.parent=self
		self.symtab=symtab
	
	def collect_uses(self):
		return self.call.collect_uses() + self.symtab.exclude([standard_types['function'],standard_types['label']])

class IfStat(Stat):
	def __init__(self, parent=None, cond=None, thenpart=None, elsepart=None, symtab=None):
		self.parent=parent
		self.cond=cond
		self.thenpart=thenpart
		self.elsepart=elsepart
		self.cond.parent=self
		self.thenpart.parent=self
		if self.elsepart : self.elsepart.parent=self
		self.symtab=symtab

	def lower(self):
		exit_label = standard_types['label']()
		exit_stat = EmptyStat(self.parent,symtab=self.symtab)
		exit_stat.setLabel(exit_label)
		if self.elsepart :
			then_label = standard_types['label']()
			self.thenpart.setLabel(else_label)
			branch_to_then = BranchStat(None,self.cond,then_label,self.symtab)
			branch_to_exit = BranchStat(None,None,exit_label,self.symtab)
			stat_list = StatList(self.parent, [branch_to_then,self.elsepart,branch_to_exit,self.thenpart,exit_stat], self.symtab)
			return self.parent.replace(self,stat_list)
		else :
			branch_to_exit = BranchStat(None,UnExpr(None,['not', self.cond]),exit_label,self.symtab)
			stat_list = StatList(self.parent, [branch_to_exit,self.thenpart,exit_stat], self.symtab)
			return self.parent.replace(self,stat_list)
						
	
class WhileStat(Stat):
	def __init__(self, parent=None, cond=None, body=None, symtab=None):
		self.parent=parent
		self.cond=cond
		self.body=body
		self.cond.parent=self
		self.body.parent=self
		self.symtab=symtab
	
	def lower(self):
		entry_label = standard_types['label']()
		exit_label = standard_types['label']()
		exit_stat = EmptyStat(self.parent,symtab=self.symtab)
		exit_stat.setLabel(exit_label)
		branch = BranchStat(None,self.cond,exit_label,self.symtab)
		branch.setLabel(entry_label)
		loop = BranchStat(None,Const(None, 1),entry_label,self.symtab)
		stat_list = StatList(self.parent, [branch,self.body,loop,exit_stat], self.symtab)
		return self.parent.replace(self,stat_list)
	
class ForStat(Stat):
	def __init__(self, parent=None, init=None, cond=None, step=None, body=None, symtab=None):
		self.parent=parent
		self.init=init
		self.cond=cond
		self.step=step
		self.body=body
		self.cond.parent=self
		self.body.parent=self
		self.target.parent=self
		self.step.parent=self
		self.symtab=symtab

class AssignStat(Stat):
	def __init__(self, parent=None, target=None, expr=None, symtab=None):
		self.parent=parent
		self.symbol=target
		self.expr=expr
		self.expr.parent=self
		self.symtab=symtab

	def collect_uses(self):
		try :	return self.expr.collect_uses()
		except AttributeError : return []

class BranchStat(Stat):
	def __init__(self, parent=None, cond=None, target=None, symtab=None):
		self.parent=parent
		self.cond=cond # cond == None -> True
		self.target=target
		self.cond.parent=self
		self.target.parent=self
		self.symtab=symtab

	def collect_uses(self):
		try : return self.cond.collect_uses()
		except AttributeError : return []

	def is_unconditional(self):	
		try :
			check=self.cond.value
			return True
		except AttributeError :
			return False

class EmptyStat(Stat):
	pass

	def collect_uses(self):
		return []

class StoreStat(Stat):
	def __init__(self, parent=None, symbol=None, symtab=None):
		self.parent=parent
		self.symbol=symbol
		self.symtab=symtab
		
	def collect_uses(self):
		return [self.symbol]

class LoadStat(Stat):
	def __init__(self, parent=None, symbol=None, symtab=None):
		self.parent=parent
		self.symbol=symbol
		self.symtab=symtab

	def collect_uses(self):
		return []

class StatList(Stat):
	def __init__(self,parent=None, children=None, symtab=None):
		print 'StatList : new', id(self)
		self.parent=parent
		if children : 
			self.children=children[:]
			for c in self.children :
				c.parent=self
		else : self.children=[]
		self.symtab=symtab
		
	def append(self, elem):
		elem.parent=self
		print 'StatList: appending', id(elem), 'of type', type(elem), 'to', id(self)
		self.children.append(elem)

	def collect_uses(self):
		return sum([ c.collect_uses() for c in self.children ])

	def print_content(self):
			print 'StatList', id(self), ': [',
			for n in self.children :
				print id(n),
			print ']'

	def flatten(self):
		'''Remove nested StatLists'''
		if type(self.parent)==StatList :
			print 'Flattening', id(self), 'into', id(self.parent)
			for c in self.children :
				c.parent=self.parent
			try : 
				label = self.getLabel()
				self.children[0].setLabel(label)
			except Exception : pass
			i = self.parent.children.index(self)
			self.parent.children=self.parent.children[:i]+self.children+self.parent.children[i+1:]
			return True
		else :
			print 'Not flattening', id(self), 'into', id(self.parent), 'of type', type(self.parent)
			return False

class Block(Stat):
	def __init__(self, parent=None, gl_sym=None, lc_sym=None, defs=None, body=None):
		self.parent=parent
		self.global_symtab=gl_sym
		self.local_symtab=lc_sym
		self.body=body
		self.defs=defs
		self.body.parent=self
		self.defs.parent=self

class PrintStat(Stat):
	def __init__(self, parent=None, symbol=None, symtab=None):	
		self.parent=parent
		self.symbol=symbol
		self.symtab=symtab

	def collect_uses(self):
		return [self.symbol]
	

#DEFINITIONS
class Definition(IRNode):
	def __init__(self, parent=None, symbol=None):
		self.parent=parent
		self.symbol=symbol

class FunctionDef(Definition):
	def __init__(self, parent=None, symbol=None, body=None):
		self.parent=parent
		self.symbol=symbol
		self.body=body
		self.body.parent=self

	def getGlobalSymbols(self):
		return self.body.global_symtab.exclude([standard_types['function'],standard_types['label']])

class DefinitionList(IRNode):
	def __init__(self,parent=None, children=None):
		self.parent=parent
		if children :	self.children=children
		else : self.children=[]
		
	def append(self, elem):
		elem.parent=self
		self.children.append(elem)
		

def print_stat_list(node):
	'''Navigation action: print'''
	print type(node), id(node)
	if type(node)==StatList :
		print 'StatList', id(node), ': [',
		for n in node.children :
			print id(n),
		print ']'
	
