#!/usr/bin/env python
# -*- encoding:utf8 -*-

import re
import os
import sys
import json
import urllib
import urllib2
import argparse
import subprocess

class DataType(object):
	
	def validate(self, val):
		return True

	def from_cli(self, val):
		return None

	def arg_parser_opts(self):
		return {}


class TupleType(DataType):
	def __init__(self, *dtypes):
		self.dtypes = map(get_data_type, dtypes)

	def validate(self, val):
		if not isinstance(val, (list, tuple)):
			return False

		if len(self.dtypes) != len(val):
			return False
		
		for dtype, citem in zip(self.dtypes, val):
			if not dtype.valid(citem):
				return False
		
		return True

	def from_cli(self, val):
		return [dtype.from_cli(citem) for dtype, citem in zip(self.dtypes, val)]

	def arg_parser_opts(self):
		return {'nargs': len(self.dtypes), 'type': str}


class ListType(DataType):
	def __init__(self, dtype):
		self.dtype = get_data_type(dtype)

	def validate(self, val):
		if not isinstance(val, (list, tuple)):
			return False

		for curr_item in val:
			if not self.dtype.valid(curr_item):
				return False
		
		return True

	def from_cli(self, val):
		return [self.dtype.from_cli(curr_item) for curr_item in val]

	def arg_parser_opts(self):
		opts = self.dtype.arg_parser_opts()
		opts['nargs'] = '*'
		return opts


class IntType(DataType):
	
	def validate(self, val):
		return isinstance(val, int)

	def from_cli(self, val):
		return int(val)

	def arg_parser_opts(self):
		return {'type': int}


class StrType(DataType):
	
	def validate(self, val):
		return isinstance(val, basestring)

	def from_cli(self, val):
		return val

	def arg_parser_opts(self):
		return {'type': str}


class IPAddr(DataType):

	def validate(self, val):
		if not isinstance(val, basestring):
			return False
		
		ip_vals = val.split('.')

		if len(vals) != 4:
			return False

		for ip_val in vals:
			try:
				vl = int(ip_val)
			except ValueError:
				return False

			if vl > 255 or vl < 0:
				return False

		return True

	def from_cli(self, val):
		if not cls.validate(val):
			raise ValueError("")
		return val

	def arg_parser_opts(self):
		return {'type': str}


types_map = {
	int : IntType,
	str : StrType
}


def get_data_type(obj):
	if isinstance(obj, DataType):
		return obj

	if isinstance(obj, list):
		assert len(obj) == 1
		return ListType(obj[0])

	if isinstance(obj, tuple):
		return TupleType(*obj)

	if issubclass(obj, DataType):
		return obj()

	return types_map[obj]()


#-------------------------------------------------------------------------------

class _NoDef(object):
	pass


class Param(object):
	def __init__(self, tp, help, default=_NoDef):
		self.name = None
		self.tp = get_data_type(tp)
		self.help = help
		self.default = default

	def validate(self, val):
		if val == self.default:
			return True
		self.tp.validate(val) 

	def from_cli(self, val):
		return self.tp.from_cli(val) 

	def arg_parser_opts(self):
		return self.tp.arg_parser_opts()

	def required(self):
		return self.default is _NoDef


def get_meta_base(cls, meta_cls):
	meta = getattr(cls, '__metaclass__', type)
	if not issubclass(meta, meta_cls):
		raise ValueError("No metaclasses derived from" + \
						 " {0} found in {1} bases".\
						 format(meta_cls.__name__, cls.__name__))
	
	for pos, cbase in enumerate(cls.mro()[1:]):
		meta = getattr(cbase, '__metaclass__', type)
		#print "issubclass({}, {}) == {}".format(meta, meta_cls, issubclass(meta, meta_cls))
		if not issubclass(meta, meta_cls):
			return cls.mro()[pos]

	print cls, meta_cls, cls.mro()

api_classes = {}

class APIMeta(type):
	def __new__(cls, name, bases, clsdict):
		global api_classes
		new_cls = super(APIMeta, cls).__new__(cls, name, bases, clsdict)
		meta_base = get_meta_base(new_cls, cls)
		
		if new_cls is not meta_base:
			api_classes[meta_base].append(new_cls)
		else:
			api_classes[meta_base] = []

		for name, param in new_cls.class_only_params():
			param.name = name

		return new_cls

	@classmethod
	def all_classes(cls, cls_base):
		return api_classes[cls_base]

class APICallBase(object):
	__metaclass__ = APIMeta
	
	def __init__(self, **dt):
		self._consume(dt)

	@classmethod
	def name(cls):
		return cls.__name__.lower()

	@classmethod
	def all_derived(cls):
		return api_classes[get_meta_base(cls, APIMeta)]

	@classmethod
	def class_only_params(cls):
		param_cls = getattr(cls, 'Params', None)
		if param_cls is not None:
			for name, param in param_cls.__dict__.items():
				if isinstance(param, Param):
					yield name, param

	@classmethod
	def all_params(cls):
		all_names = set()
		for currcls in cls.mro():
			if hasattr(currcls, 'class_only_params'):
				for name, param in currcls.class_only_params():
					if name not in all_names:
						all_names.add(name)
						yield param

	def rest_url(self):
		return '/{0}'.format(self.name())

	@classmethod
	def from_dict(cls, data):
		obj = cls.__new__(cls)
		obj._consume(data)
		return obj

	def _consume(self, data):
		required_param_names = set()
		all_param_names = set()
		for param in self.all_params():
			if param.required():
				required_param_names.add(param.name)
			all_param_names.add(param.name)

		extra_params = set(data.keys()) - all_param_names
		if extra_params != set():
			raise ValueError("Extra parameters {0} for cmd {1}".format(
							 ','.join(extra_params), self.__class__.__name__))

		missed_params = required_param_names - set(data.keys())
		if missed_params != set():
			raise ValueError("Missed parameters {0} for cmd {1}".format(
							 ','.join(missed_params), self.__class__.__name__))

		parsed_data = {}
		for param in self.all_params():
			try:
				parsed_data[param.name] = param.from_cli(data[param.name])
			except KeyError:
				parsed_data[param.name] = param.default

		self.__dict__.update(parsed_data)
		return self

	def to_dict(self):
		res = {}
		for param in self.all_params():
			res[param.name] = getattr(self,  param.name)
		return res

	def update_cli(self, subcomand):
		pass

	def execute(self):
		pass

	def __str__(self):
		res = "{0}({{0}})".format(self.__class__.__name__)
		params = ["{0}={1!r}".format(param.name, getattr(self, param.name))
						for param in self.all_params()]
		return res.format(', '.join(params))

	def __repr__(self):
		return str(self)


class Add(APICallBase):	
	"Add two integers"
	class Params(object):
		params = Param([int], "list of integers to make a sum")

	def execute(self):
		return sum(self.params)


class Sub(APICallBase):
	"Substitute two integers"
	class Params(object):
		params = Param((int, int), "substitute second int from first")

	def execute(self):
		return self.params[0] - self.params[1]


class Ping(APICallBase):
	"Ping host"
	class Params(object):
		ip = Param(IPAddr, "ip addr to ping")
		num_pings = Param(int, "number of pings", default=3)

	def execute(self):
		res = subprocess.check_stdout('ping -c {0} {1}'.format(self.num_pings, 
																 self.ip))
		return sum(map(float, re.findall(r'time=(\d+\.?\d*)', out))) / \
							self.num_pings


def get_arg_parser():
	parser = argparse.ArgumentParser()
	subparsers = parser.add_subparsers()
	for call in APIMeta.all_classes(APICallBase):
		sub_parser = subparsers.add_parser(call.name(), 
										   help=call.__doc__)
		sub_parser.set_defaults(cmd_class=call)
		for param in call.all_params():
			opts = {'help':param.help}

			if param.default is not _NoDef:
				opts['default'] = param.default
			
			opts.update(param.arg_parser_opts())
			sub_parser.add_argument('--' + param.name.replace('_', '-'),
							    **opts)
	return parser, subparsers


import cherrypy as cp
def get_cherrypy_server():
	
	class Server(object):
		pass

	def call_me(cmd_class):
		@cp.tools.json_out()
		def do_call(self, opts):
			cmd = cmd_class.from_dict(json.loads(opts))
			return cmd.execute()
		return do_call

	for call in APIMeta.all_classes(APICallBase):
		setattr(Server, 
				call.name(), 
				cp.expose(call_me(call)))

	return Server


def main(argv=None):
	argv = argv if argv is not None else sys.argv
	parser, subparsers = get_arg_parser()

	sub_parser = subparsers.add_parser('start-server', 
										help="Start REST server")
	sub_parser.set_defaults(cmd_class='start-server')

	rest_url = os.environ.get('REST_SERVER_URL', None)

	res = parser.parse_args(argv)
	cmd_cls = res.cmd_class

	if cmd_cls == 'start-server':
		rest_server = get_cherrypy_server()
		cp.quickstart(rest_server())
	else:
		for opt in cmd_cls.all_params():
			data = {}
			try:
				data[opt.name] = getattr(res, opt.name.replace('_', '-'))
			except AttributeError:
				pass
		cmd = cmd_cls.from_dict(data)

		if rest_url is None:
			print "Execute locally"
			print "Res =", cmd.execute()
		else:
			print "Remote execution"
			params = urllib.urlencode({'opts': json.dumps(cmd.to_dict())})
			res = urllib2.urlopen("http://{0}{1}?{2}".format(rest_url, 
														     cmd.rest_url(),
														     params)).read()
			print "Res =", json.loads(res)


	return 0


if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))









