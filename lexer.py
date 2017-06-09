#!/usr/bin/python

__doc__='''Simple lexer for PL/0 using generators'''

# Tokens can have multiple definitions if needed
symbols =  { 
  'lparen' : ['('], 
  'rparen' : [')'], 
  'lspar'  : ['['],
  'rspar'  : [']'],
  'colon'  : [':'],
  'times'  : ['*'], 
  'slash'  : ['/'], 
  'plus'   : ['+'], 
  'minus'  : ['-'], 
  'eql'    : ['='], 
  'neq'    : ['!='], 
  'lss'    : ['<'], 
  'leq'    : ['<='],   
  'gtr'    : ['>'], 
  'geq'    : ['>='], 
  'callsym': ['call'], 
  'beginsym'  : ['begin'], 
  'semicolon' : [';'], 
  'endsym'    : ['end'], 
  'ifsym'     : ['if'], 
  'whilesym'  : ['while'], 
  'becomes'   : [':='], 
  'thensym'   : ['then'], 
  'dosym'     : ['do'], 
  'constsym'  : ['const'], 
  'comma'     : [','], 
  'varsym'    : ['var'], 
  'procsym'   : ['procedure'], 
  'period'    : ['.'], 
  'oddsym'    : ['odd'],
  'print'     : ['!', 'print'],
}

def token(word):
  '''Return corresponding token for a given word'''
  for s in symbols : 
    if word in symbols[s] :
      return s
  try : # If a terminal is not one of the standard tokens but can be converted to float, then it is a number, otherwise, an identifier
    int(word)
    return 'number'
  except ValueError, e :
    return 'ident'

def lexer(text) :
  '''Generator implementation of a lexer'''
  import re
  from string import split, strip, lower, join
  t=re.sub('(\{[^\}]*\})', '', text) # remove comments in the *worst possible way*
  t=re.split('(\W+)',t) # Split at non alphanumeric sequences
  text=join(t,' ') # Join alphanumeric and non-alphanumeric, with spaces
  words=[ strip(w) for w in split(lower(text)) ] # Split tokens
  for word in words :
    yield token(word), word


# Test support
__test_program='''VAR x, y, squ;
VAR arr[5] : char;
var multid[5] [5] : short;

{beware of spaces because the lexer wants them!!! }
 
PROCEDURE square;
VAR test;
BEGIN
   test := 1234;
   squ := x * x
END;
 
BEGIN
   x := 1;
   WHILE x <= 10 DO
   BEGIN
      CALL square;
      x := x + 1 - 2 * x;
      !squ
   END;
   
   x := 101;
   while x <= 105 do begin
    arr[x - 100] := x;
    !arr[x - 100] 
   end;
   
   x := 1;
   y := 1;
   while x <= 5 do begin
    while y <= 5 do begin
      multid[x] [y] := arr[x] ;
      !multid[x] [y]
    end
  end
END.'''

if __name__ == '__main__' :
  for t,w in lexer(__test_program) :
    print t, w
