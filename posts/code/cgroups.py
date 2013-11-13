#!/usr/bin/env python
import os
import sys
import os.path

from ctypes import CDLL,c_int,c_void_p,c_char_p,POINTER,Structure,py_object,\
    c_float, c_ulonglong, c_ushort, c_uint8,c_uint
import pycparser

class DLLWrapper(object):
	typesmap = {
		'int': c_int,
		'void': None,
		'const char *': c_char_p,
		'char **': POINTER(c_char_p)
	}

	def __init__(self, name):
		self.name = name
		self.dll = CDLL(self.name)
		self.parser = pycparser.CParser()

	def param_type(self, param):
		res = param.quals[:]
		
		pdecl = ""

		while isinstance(param.type, pycparser.c_ast.PtrDecl):
			pdecl += '*'
			param = param.type

		tp = param.type.type.names[0]
		
		if pdecl != "":
			return " ".join(res + [tp, pdecl])

		return " ".join(res + [tp])		


	def __lshift__(self, text):
		assert isinstance(text, basestring)
		if not text.endswith(';'):
			text += ';'

		ccode = self.parser.parse(text).ext[0]
		assert isinstance(ccode.type, pycparser.c_ast.FuncDecl)

		fdecl = ccode.type
		name = fdecl.type.declname
		result = fdecl.type.type.names[0]

		params = []
		for param in fdecl.args.params:
			params.append((param.name, self.param_type(param)))

		func = getattr(self.dll, name)
		func.restype = self.typesmap[result]
		func.params = [self.typesmap[tp] for _, tp in params]

		setattr(self, name, func)
		print "{0}({2}) => {1}".format(name, result, ','.join("{1} {0}".format(*i) for i in params))


cgroups = DLLWrapper('/lib/libcgroup.so.1')

cgroups << "int cgroup_init(void)"
cgroups << "int cgroup_get_subsys_mount_point(const char *controller, char ** mount_point)"

print cgroups.cgroup_init()




