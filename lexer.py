#!/usr/bin/python

__doc__='''Simple lexer for PL/0 using generators'''

# Tokens can have multiple definitions if needed
symbols =  { 
	'lparen' : ['('], 
	'rparen' : [')'], 
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
	'print'			: ['!', 'print'],
}

def token(word):
	'''Return corresponding token for a given word'''
	for s in symbols : 
		if word in symbols[s] :
			return s
	try : # If a terminal is not one of the standard tokens but can be converted to float, then it is a number, otherwise, an identifier
		float(word)
		return 'number'
	except ValueError, e :
		return 'ident'

def lexer(text) :
	'''Generator implementation of a lexer'''
	import re
	from string import split, strip, lower, join
	t=re.split('(\W+)',text) # Split at non alphanumeric sequences
	text=join(t,' ') # Join alphanumeric and non-alphanumeric, with spaces
	words=[ strip(w) for w in split(lower(text)) ] # Split tokens
	for word in words :
		yield token(word), word


# Test support
__test_program='''VAR x, squ;
 
PROCEDURE square;
BEGIN
   squ := x * x
END;
 
BEGIN
   x := 1;
   WHILE x <= 10 DO
   BEGIN
      CALL square;
      x := x + 1 ;
			!squ
   END
END.'''

if __name__ == '__main__' :
	for t,w in lexer(__test_program) :
		print t, w
