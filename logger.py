#!/usr/bin/python

__doc__ = '''Logging function using decorators
Usage: decorate monitored function with "@logger"'''

def logger(f):
	def wrapped(*args, **kwargs):
		print 'start', f
		res = f(*args, **kwargs)
		print 'end', f
		return res
	return wrapped
