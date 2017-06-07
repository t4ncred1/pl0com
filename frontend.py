#!/usr/bin/python

__doc__ = '''PL/0 recursive descent parser adapted from Wikipedia'''

from ir import *
from logger import logger

symbols =  [ 'ident', 'number', 'lparen', 'rparen', 'times', 'slash', 'plus', 
'minus', 'eql', 'neq', 'lss', 'leq', 'gtr', 'geq', 'callsym', 'beginsym', 
'semicolon', 'endsym', 'ifsym', 'whilesym', 'becomes', 'thensym', 'dosym', 
'constsym', 'comma', 'varsym', 'procsym', 'period', 'oddsym' ]

sym = None
value = None
new_sym = None
new_value = None

def getsym():
  '''Update sym'''
  global new_sym 
  global new_value
  global sym
  global value
  try :
    sym=new_sym
    value=new_value
    new_sym, new_value=the_lexer.next()
  except StopIteration :
    return 2
  print 'getsym:', new_sym, new_value
  return 1
  
def error(msg):
  print '\033[31m', msg, new_sym, new_value, '\033[39m'
  
def accept(s):
  print 'accepting', s, '==', new_sym
  return getsym() if new_sym==s else 0
 
def expect(s) :
  print 'expecting', s
  if accept(s) : return 1
  error("expect: unexpected symbol")
  return 0
  
  
def linearizeMultidVector(explist, target, symtab):
  offset=None
  for i in range(0, len(target.stype.dims)):
    if i + 1 < len(target.stype.dims):
      planedisp = reduce(lambda x,y: x*y, target.stype.dims[i+1:])
    else:
      planedisp = 1
    idx = explist[i]
    esize = (target.stype.basetype.size / 8) * planedisp;
    planed = BinExpr(children=['times', idx, Const(value=esize, symtab=symtab)], symtab=symtab)
    if offset == None:
      offset = planed
    else:
      offset = BinExpr(children=['plus', offset, planed], symtab=symtab)
  return offset

 
@logger
def factor(symtab) :
  if accept('ident') :
    var = symtab.find(value)
    if (isinstance(var.stype, ArrayType)):
      vidx = []
      for i in var.stype.dims:
        expect('lspar')
        vidx.append(expression(symtab))
        expect('rspar')
      offset = linearizeMultidVector(vidx, var, symtab)
      return ArrayElement(var=var, offset=offset, symtab=symtab)
    else:
      return Var(var=var, symtab=symtab)
  if accept('number') : return Const(value=value, symtab=symtab)
  elif accept('lparen') :
    expr = expression()
    expect('rparen')
    return expr
  else :
    error("factor: syntax error")
    getsym()
 
@logger
def term(symtab) :
  op=None
  expr = factor(symtab)
  while new_sym in [ 'times', 'slash'] :
    getsym()
    op = sym
    expr2 = factor(symtab)
    expr = BinExpr(children=[ op, expr, expr2 ], symtab=symtab)
  return expr
 
@logger
def expression(symtab) :
  op=None
  if new_sym in [ 'plus', 'minus' ] :
    getsym()
    op = sym
  expr = term(symtab)
  if op : expr = UnExpr(children=[initial_op, expr], symtab=symtab)
  while new_sym in [ 'plus', 'minus' ] :
    getsym()
    op = sym
    expr2 = term(symtab)
    expr = BinExpr(children=[ op, expr, expr2 ], symtab=symtab)
  return expr
 
@logger
def condition(symtab) :
  if accept('oddsym') : 
    return UnExpr(children=['odd', expression(symtab)], symtab=symtab)
  else :
    expr = expression(symtab);
    if new_sym in [ 'eql', 'neq', 'lss', 'leq', 'gtr', 'geq' ] :
      getsym()
      print 'condition operator', sym, new_sym
      op=sym
      expr2 = expression(symtab)
      return BinExpr(children=[op, expr, expr2 ], symtab=symtab)
    else :
      error("condition: invalid operator")
      getsym();
 
@logger
def statement(symtab) :
  if accept('ident') :
    target=symtab.find(value)
    offset=None
    if isinstance(target.stype, ArrayType):
      idxes = []
      for i in range(0, len(target.stype.dims)):
        expect('lspar')
        idxes.append(expression(symtab))
        expect('rspar')
      offset = linearizeMultidVector(idxes, target, symtab)
    expect('becomes')
    expr=expression(symtab)
    return AssignStat(target=target, offset=offset, expr=expr, symtab=symtab)
    
  elif accept('callsym') :
    expect('ident')
    return CallStat(call_expr=CallExpr(function=symtab.find(value), symtab=symtab), symtab=symtab)
  elif accept('beginsym') :
    statement_list = StatList(symtab=symtab)
    statement_list.append(statement(symtab))
    while accept('semicolon') :
      statement_list.append(statement(symtab))
    expect('endsym');
    statement_list.print_content()
    return statement_list
  elif accept('ifsym') :
    cond=condition()
    expect('thensym')
    then=statement(symtab)
    return IfStat(cond=cond,thenpart=then, symtab=symtab)
  elif accept('whilesym') :
    cond=condition(symtab)
    expect('dosym')
    body=statement(symtab)
    return WhileStat(cond=cond, body=body, symtab=symtab)
  elif accept('print') :
    exp=expression(symtab)
    return PrintStat(exp=exp,symtab=symtab)

 
@logger
def block(symtab, alloct='auto') :
  local_vars = SymbolTable()
  defs = DefinitionList()
  
  while accept('constsym') or accept('varsym'):
    if (sym == 'constsym'):
      constdef(local_vars, alloct)
      while accept('comma'):
        constdef(local_vars, alloct)
    else:
      vardef(local_vars, alloct)
      while accept('comma'):
        vardef(local_vars, alloct)
    expect('semicolon')

  while accept('procsym') :
    expect('ident')
    fname=value
    expect('semicolon');
    local_vars.append(Symbol(fname, standard_types['function']))
    fbody=block(local_vars)
    expect('semicolon')
    defs.append(FunctionDef(symbol=local_vars.find(fname), body=fbody))
  stat = statement(SymbolTable(symtab[:]+local_vars))
  return Block(gl_sym=symtab, lc_sym=local_vars, defs=defs, body=stat)
  
  
@logger
def constdef(local_vars, alloct='auto'):
  expect('ident')
  name=value
  expect('eql')
  expect('number')
  local_vars.append(Symbol(name, standard_types['int'], alloct=alloct), value)
  while accept('comma') :
    expect('ident')
    name=value
    expect('eql')
    expect('number')
    local_vars.append(Symbol(name, standard_types['int'], alloct=alloct), value)
    
  
@logger
def vardef(symtab, alloct='auto'):
  expect('ident')
  name = value
  size = []
  while accept('lspar'):
    expect('number')
    size.append(int(value))
    expect('rspar')
    
  type = standard_types['int']
  if accept('colon'):
    accept('ident')
    type = standard_types[value]
    
  if len(size) > 0:
    symtab.append(Symbol(name, ArrayType(name, size, type), alloct=alloct))
  else:
    symtab.append(Symbol(name, type, alloct=alloct))
  
 
@logger
def program() :
  '''Axiom'''
  global_symtab=SymbolTable()
  getsym()
  the_program = block(global_symtab, 'global')
  expect('period')
  return the_program



if __name__ == '__main__' :
  from lexer import lexer, __test_program
  the_lexer=lexer(__test_program)
  res = program()
  print '\n', res, '\n'
      
  res.navigate(print_stat_list)
  from support import *


  node_list=get_node_list(res)
  for n in node_list :
    print type(n), id(n), '->', type(n.parent), id(n.parent)
  print '\nTotal nodes in IR:', len(node_list), '\n'

  res.navigate(lowering)

  node_list=get_node_list(res)
  print '\n', res, '\n'
  for n in node_list :
    print type(n), id(n)
    try : n.flatten()
    except Exception :  pass
  #res.navigate(flattening)
  print '\n', res, '\n'

  print_dotty(res,"log.dot")
  
  from datalayout import *
  print "\n\nDATALAYOUT\n\n"
  performDataLayout(res)
  print '\n', res, '\n'

  from cfg import *
  cfg=CFG(res)
  cfg.liveness()
  cfg.print_liveness()
  cfg.print_cfg_to_dot("cfg.dot")
   
  from regalloc import *
  print "\n\nREGALLOC\n\n"
  ra = minimal_register_allocator(cfg,8)
  reg_alloc = ra()
  print reg_alloc
  
  from codegen import *
  print "\n\nCODEGEN\n\n"
  print generateCode(res, reg_alloc)
  
  
