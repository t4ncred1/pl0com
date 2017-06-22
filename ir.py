#!/usr/bin/python

__doc__='''Intermediate Representation
Could be improved by relying less on class hierarchy and more on string tags and/or duck typing
Includes lowering and flattening functions'''

# Every node must have a lowering function or a code generation function.
# Assign statements are more complex than they seem; they typically translate
# to a store stmt, with the symbol and a temporary as parameters. Var translates
# to a load statement to the same temporary that is used in a following stage
# for doing the computations. The expression tree gets flattened to a stmt list
# larger expressions: last temporary used is the result

from regalloc import *
from codegenhelp import *
from datalayout import *

#SYMBOLS AND TYPES
basetypes = [ 'Int', 'Float', 'Label', 'Struct', 'Function' ]
qualifiers = [ 'unsigned' ]



# UTILITIES

tempcount = 0
def newTemporary(symtab, type):
  global tempcount
  temp = Symbol(name='t'+str(tempcount), stype=type, alloct='reg')
  tempcount += 1
  return temp



# TYPES

class Type(object):
  def __init__(self, name, size, basetype, qualifiers=[]):
    self.name=name
    self.size=size
    self.basetype=basetype
    self.qual_list=qualifiers

class ArrayType(Type):
  def __init__(self, name, dims, basetype):
    # dims: set of dimensions: dims = [5] array; dims = [5, 5] matrix...
    self.name=name
    self.dims=dims
    self.size=reduce(lambda a, b: a*b, dims) * basetype.size
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
  #'float': Type('float', 32, 'Float'),
  'label': LabelType(),
  'function' : FunctionType(),
}


alloctype = [ 'global', 'auto', 'reg', 'imm' ]   # mem -> auto, global
class Symbol(object):
  # may be assigned to either:
  #  - a register
  #  - a memory location
  #  - an immediate (but this is produced by later optimizations)
  def __init__(self, name, stype, value=None, alloct='auto'):
    self.name=name
    self.stype=stype
    self.value=value # if not None, it is a constant
    self.alloct=alloct
    self.allocinfo = None
    
  def setAllocInfo(self, allocinfo):
    self.allocinfo = allocinfo

  def __repr__(self):
    base = self.alloct + ' ' + self.stype.name + ' ' + self.name + \
           ( self.value if type(self.value)==str else '')
    if not self.allocinfo is None:
      base = base + "; " + `self.allocinfo`
    return base
    

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



# IRNODE

class IRNode(object):

  def __init__(self,parent=None, children=None, symtab=None):
    self.parent=parent
    if children : 
      self.children=children
      for c in self.children:
        try:
          c.parent = self
        except Exception:
          pass
    else : 
      self.children=[]
    self.symtab=symtab
  
  
  def __repr__(self):
    from string import split, join
    
    try :
      label=self.getLabel().name + ': '
    except Exception, e :
      label=''
      pass
    try:
      hre = self.humanRepr()
      return label + hre
    except Exception:
      pass
    
    attrs = set(['body','cond', 'value','thenpart','elsepart', 'symbol', 'call', 'step', 'expr', 'target', 'defs', 'global_symtab', 'local_symtab', 'offset' ]) & set(dir(self))

    res=`type(self)`+' '+`id(self)`+' {\n'
    if self.parent != None:
      res += 'parent = ' + `id(self.parent)` + '\n'
    else:
      res += '                                                                      <<<<<----- BUG? MISSING PARENT\n'
      
    res=label+res
      
    #print 'NODE', type(self), id(self)
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
    attrs = set(['body','cond', 'value','thenpart','elsepart', 'symbol', 'call', 'step', 'expr', 'target', 'defs', 'global_symtab', 'local_symtab', 'offset']) & set(dir(self))
    if 'children' in dir(self) and len(self.children) :
      print 'navigating children of', type(self), id(self), len(self.children)
      for node in self.children :
        try : node.navigate(action)
        except Exception : pass
    for d in attrs :
      try :
        getattr(self,d).navigate(action)
        print 'successfully navigated attr ',d,' of', type(self), id(self)
      except Exception : pass
    action(self)
  
  
  def replace(self, old, new):
    new.parent = self
    if 'children' in dir(self) and len(self.children) and old in self.children:
      self.children[self.children.index(old)]=new
      return True
    attrs = set(['body','cond', 'value','thenpart','elsepart', 'symbol', 'call', 'step', 'expr', 'target', 'defs', 'global_symtab', 'local_symtab', 'offset']) & set(dir(self))
    for d in attrs :
      try :
        if getattr(self,d)==old :
          setattr(self,d,new)
          return True     
      except Exception :
        pass
    return False
    
    
  def getFunction(self):
    if not self.parent : return 'global'
    elif type(self.parent)== FunctionDef :
      return self.parent
    else :
      return self.parent.getFunction()
      

#CONST and VAR  

class Const(IRNode):
  def __init__(self,parent=None, value=0, symb=None, symtab=None):
    self.parent=parent
    self.value=value
    self.symbol=symb
    self.symtab=symtab
    
  def lower(self):
    if (self.symbol == None):
      new = newTemporary(self.symtab, standard_types['int'])
      loadst = LoadImmStat(dest=new, val=self.value, symtab=self.symtab)
    else:
      new = newTemporary(self.symtab, self.symbol.stype)
      loadst = LoadStat(dest=new, symbol=self.symbol, symtab=self.symtab)
    return self.parent.replace(self, StatList(children=[loadst], symtab=self.symtab))
    
    
class Var(IRNode):
  # loads in a temporary the value pointed to by the symbol
  def __init__(self,parent=None, var=None, symtab=None):
    self.parent=parent
    self.symbol=var
    self.symtab=symtab

  def collect_uses(self):
    return [self.symbol]
    
  def lower(self):
    new = newTemporary(self.symtab, self.symbol.stype)
    loadst = LoadStat(dest=new, symbol=self.symbol, symtab=self.symtab)
    return self.parent.replace(self, StatList(children=[loadst], symtab=self.symtab))
    
    
class ArrayElement(IRNode):
  # loads in a temporary the value pointed by: the symbol + the index
  def __init__(self, parent=None, var=None, offset=None, symtab=None):
    # offset can NOT be a list of exps in case of multi-d arrays
    self.parent=parent
    self.symbol=var
    self.symtab=symtab
    self.offset=offset
    self.offset.parent = self
    
  def collect_uses(self):
    a = [self.symbol]
    a += self.offset.collect_uses()
    return a
    
  def lower(self):
    global standard_types
    dest = newTemporary(self.symtab, self.symbol.stype)
    off = self.offset.destination()
    
    statl = [self.offset]
    
    ptrreg = newTemporary(self.symtab, standard_types['uint'])
    loadptr = LoadPtrToSym(dest=ptrreg, symbol=self.symbol, symtab=self.symtab)
    src = newTemporary(self.symtab, standard_types['uint'])
    add = BinStat(dest=src, op='plus', srca=ptrreg, srcb=off, symtab=self.symtab)
    statl += [loadptr, add]
    
    statl += [LoadStat(dest=dest, symbol=src, symtab=self.symtab)]  
    return self.parent.replace(self, StatList(children=statl, symtab=self.symtab))
    
    
#EXPRESSIONS

class Expr(IRNode):
  # ABSTRACT
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
    
  def lower(self):
    srca = self.children[1].destination();
    srcb = self.children[2].destination();
    
    # type promotion
    if srca.stype.basetype == 'Float' or srcb.stype.basetype == 'Float':
      desttype = Type('', max(srca.stype.size, srcb.stype.size), 'Float')
    else:
      if (srca.stype.qual_list != None and 'unsigned' in srca.stype.qual_list) \
          and \
         (srcb.stype.qual_list != None and 'unsigned' in srcb.stype.qual_list):
        desttype = Type('', max(srca.stype.size, srcb.stype.size), 'Int', ['unsigned'])
      else:
        desttype = Type('', max(srca.stype.size, srcb.stype.size), 'Int')
    
    dest = newTemporary(self.symtab, desttype)
    
    stmt = BinStat(dest=dest, op=self.children[0], srca=srca, srcb=srcb, symtab=self.symtab)
    statl = [self.children[1], self.children[2], stmt]
    return self.parent.replace(self, StatList(children=statl, symtab=self.symtab))


class UnExpr(Expr):
  def getOperand(self):
    return self.children[1]
    
  def lower(self):
    src = self.children[1].destination();
    dest = newTemporary(self.symtab, src.stype)
    stmt = UnaryStat(dest=dest, op=self.children[0], src=src, symtab=self.symtab)
    statl = [self.children[1], stmt]
    return self.parent.replace(self, StatList(children=statl, symtab=self.symtab))


class CallExpr(Expr):
  def __init__(self, parent=None, function=None, parameters=None, symtab=None):
    self.parent=parent
    self.symbol=function
    # parameters are ignored
    if parameters : self.children=parameters[:]
    else : self.children=[]


# STATEMENTS

class Stat(IRNode):
  # ABSTRACT
  def setLabel(self, label):
    self.label=label
    label.value=self # set target
  
  def getLabel(self):
    return self.label
    
  def collect_uses(self):
    return []
    
  def collect_kills(self):
    return []
      

class CallStat(Stat):
  '''Procedure call (non returning)'''
  def __init__(self, parent=None, call_expr=None, symtab=None):
    self.parent=parent
    self.call=call_expr
    self.call.parent=self
    self.symtab=symtab
  
  def collect_uses(self):
    return self.call.collect_uses() + self.symtab.exclude([standard_types['function'],standard_types['label']])
    
  def lower(self):
    dest = self.call.symbol
    bst = BranchStat(target=dest, symtab=self.symtab, returns=True)
    return self.parent.replace(self, bst)


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
      branch_to_then = BranchStat(None,self.cond.destination(),then_label,self.symtab)
      branch_to_exit = BranchStat(None,None,exit_label,self.symtab)
      stat_list = StatList(self.parent, [self.cond,branch_to_then,self.elsepart,branch_to_exit,self.thenpart,exit_stat], self.symtab)
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
    self.cond.setLabel(entry_label)
    branch = BranchStat(None,self.cond.destination(),exit_label,self.symtab)
    loop = BranchStat(None,None,entry_label,self.symtab)
    stat_list = StatList(self.parent, [self.cond, branch,self.body,loop,exit_stat], self.symtab)
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
  def __init__(self, parent=None, target=None, offset=None, expr=None, symtab=None):
    self.parent=parent
    self.symbol=target
    try:
      self.symbol.parent = self
    except AttributeError:
      pass
    self.expr=expr
    self.expr.parent=self
    self.symtab=symtab
    self.offset=offset
    if self.offset != None:
      self.offset.parent = self

  def collect_uses(self):
    try:
      a = self.symbol.collect_uses()
    except AttributeError:
      a = []
    try:
      a += self.offset.collect_uses()
    except AttributeError: pass
    try: 
      return a + self.expr.collect_uses()
    except AttributeError: 
      return a
  
  def collect_kills(self):
    return [self.symbol]
    
  def lower(self):
    src = self.expr.destination()
    dst = self.symbol
    
    stats = [self.expr]
    
    if self.offset:
      off = self.offset.destination()
      ptrreg = newTemporary(self.symtab, standard_types['uint'])
      loadptr = LoadPtrToSym(dest=ptrreg, symbol=dst, symtab=self.symtab)
      dst = newTemporary(self.symtab, standard_types['uint'])
      add = BinStat(dest=dst, op='plus', srca=ptrreg, srcb=off, symtab=self.symtab)
      stats += [self.offset, loadptr, add]
      
    stats += [StoreStat(dest=dst, symbol=src, symtab=self.symtab)]

    return self.parent.replace(self, StatList(children=stats, symtab=self.symtab))
    
    
class PrintStat(Stat):
  def __init__(self, parent=None, exp=None, symtab=None):  
    self.parent=parent
    self.expr=exp
    self.symtab=symtab
    exp.parent = self

  def collect_uses(self):
    return self.expr.collect_uses()
    
  def lower(self):
    pc = PrintCommand(src=self.expr.destination(), symtab=self.symtab)
    stlist = StatList(children=[self.expr, pc], symtab=self.symtab)
    return self.parent.replace(self, stlist)
    
    
class PrintCommand(Stat):   # ll
  def __init__(self, parent=None, src=None, symtab=None):
    self.parent=parent
    self.src=src
    if src.alloct != 'reg':
      raise RuntimeError('value not in register')
    self.symtab = symtab
    
  def collect_uses(self):
    return [self.src]

  def humanRepr(self):
    return 'print ' + `self.src`


class BranchStat(Stat):   # ll
  def __init__(self, parent=None, cond=None, target=None, symtab=None, returns=False):
    self.parent=parent
    self.cond=cond # cond == None -> True
    if not (self.cond is None) and self.cond.alloct != 'reg':
      raise RuntimeError('condition not in register')
    self.target=target
    self.symtab=symtab
    self.returns = returns

  def collect_uses(self):
    if not (self.cond is None):
      return [self.cond]
    return []

  def is_unconditional(self): 
    if self.cond is None:
      return True
    return False
      
  def humanRepr(self):
    if self.returns:
      h = 'call '
    else:
      h = 'branch '
    if not (self.cond is None):
      c = 'on ' + `self.cond`
    else:
      c = ''
    return h + c + ' to ' + `self.target`
      

class EmptyStat(Stat):  # ll
  pass

  def collect_uses(self):
    return []
    
    
class LoadPtrToSym(Stat):  # ll
  def __init__(self, parent=None, dest=None, symbol=None,  symtab=None):
    self.parent = parent
    self.symbol = symbol
    self.symtab = symtab
    self.dest = dest
    if self.symbol.alloct == 'reg':
      raise RuntimeError('symbol not in memory')
    if self.dest.alloct != 'reg':
      raise RuntimeError('dest not to register')
      
  def collect_uses(self):
    return [self.symbol]
    
  def collect_kills(self):
    return [self.dest]
    
  def destination(self):
    return self.dest
    
  def humanRepr(self):
    return `self.dest` + ' <- &(' + `self.symbol` + ')'


class StoreStat(Stat):  # ll
  # store the symbol to the specified destination + offset
  def __init__(self, parent=None, dest=None, symbol=None, killhint=None, symtab=None):
    self.parent=parent
    self.symbol=symbol
    if self.symbol.alloct != 'reg':
      raise RuntimeError('store not from register')
    self.symtab=symtab
    self.dest = dest
    self.killhint = killhint
    
  def collect_uses(self):
    if self.dest.alloct == 'reg':
      return [self.symbol, self.dest]
    return [self.symbol]
    
  def collect_kills(self):
    if self.dest.alloct == 'reg':
      if self.killhint:
        return [self.killhint]
      else:
        return []
    return [self.dest]
    
  def destination(self):
    return self.dest
  
  def humanRepr(self):
    if self.dest.alloct == 'reg':
      return '[' + `self.dest` + '] <- ' + `self.symbol`
    return `self.dest` + ' <- ' + `self.symbol`


class LoadStat(Stat):  # ll
  # load the value pointed to by the specified symbol + offset
  def __init__(self, parent=None, dest=None, symbol=None, usehint=None, symtab=None):
    self.parent=parent
    self.symbol=symbol
    self.symtab=symtab
    self.dest = dest
    self.usehint = usehint
    if self.dest.alloct != 'reg':
      raise RuntimeError('load not to register')

  def collect_uses(self):
    if self.usehint:
      return [self.symbol, self.usehint]
    return [self.symbol]
    
  def collect_kills(self):
    return [self.dest]
    
  def destination(self):
    return self.dest
    
  def humanRepr(self):
    if self.symbol.alloct == 'reg':
      return `self.dest` + ' <- [' + `self.symbol` + ']'
    else:
      return `self.dest` + ' <- ' + `self.symbol`
    
    
class LoadImmStat(Stat):  # ll
  def __init__(self, parent=None, dest=None, val=0, symtab=None):
    self.parent=parent
    self.val = val
    self.dest = dest
    if self.dest.alloct != 'reg':
      raise RuntimeError('load not to register')
  
  def collect_uses(self):
    return []
    
  def collect_kills(self):
    return [self.dest]
    
  def destination(self):
    return self.dest
    
  def humanRepr(self):
    return `self.dest` + ' <- ' + `self.val`
    
    
class BinStat(Stat):  # ll
  def __init__(self, parent=None, dest=None, op=None, srca=None, srcb=None, symtab=None):
    self.parent = parent
    self.dest = dest   # symbol
    self.op = op       
    self.srca = srca   # symbol
    self.srcb = srcb   # symbol
    if self.dest.alloct != 'reg':
      raise RuntimeError('binstat dest not to register')
    if self.srca.alloct != 'reg' or self.srcb.alloct != 'reg':
      raise RuntimeError('binstat src not in register')
    self.symtab = symtab
    
  def collect_kills(self):
    return [self.dest]
    
  def collect_uses(self):
    return [self.srca, self.srcb]
  
  def destination(self):
    return self.dest
    
  def humanRepr(self):
    return `self.dest` + ' <- ' + `self.srca` + ' ' + self.op + ' ' + `self.srcb`
    
    
class UnaryStat(Stat):  # ll
  def __init__(self, parent=None, dest=None, op=None, src=None, symtab=None):
    self.parent = parent
    self.dest = dest
    self.op = op
    self.src = src
    self.symtab = symtab
    if self.dest.alloct != 'reg':
      raise RuntimeError('unarystat dest not to register')
    if self.src.alloct != 'reg':
      raise RuntimeError('unarystat src not in register')
    
  def collect_kills(self):
    return [self.dest]
    
  def collect_uses(self):
    return [self.src]
    
  def destination(self):
    return self.dest
    
  def humanRepr(self):
    return `self.dest` + ' <- ' + self.op + ' ' + `self.src`


class StatList(Stat):  # ll
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
    u = []
    for c in self.children:
      u += c.collect_uses()
    return u
    
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
      
  def destination(self):
    for i in range(-1, -len(self.children)-1, -1):
      try:
        return self.children[i].destination()
      except Exception:
        pass
    return None
      
      

class Block(Stat):
  def __init__(self, parent=None, gl_sym=None, lc_sym=None, defs=None, body=None):
    self.parent=parent
    self.global_symtab=gl_sym
    self.local_symtab=lc_sym
    self.body=body
    self.defs=defs
    self.body.parent=self
    self.defs.parent=self
    self.stackroom = 0

  

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
    if children : self.children=children
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
  
