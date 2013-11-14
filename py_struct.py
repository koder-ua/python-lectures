class StructMeta(type):
	def __new__(cls, name, bases, dct):
		if name != 'Struct':
			
			mandatory_attrs = []
			optional_attrs = []

			attrs = dct['attrs'].replace(" ", "")
			attrs = attrs.replace("\t", "")

			if '[' in attrs:
				m_arttrs, opt_attrs = attrs.split('[')
				assert opt_attrs.endswith(']')
				assert opt_attrs.startswith(',')
				mandatory_attrs = m_arttrs.split(',')
				optional_attrs = opt_attrs[1:-1].split(',')
			else:
				mandatory_attrs = attrs.split(',')
				optional_attrs = []
			
			all_attrs = mandatory_attrs + optional_attrs
								
			init_attrs = ", ".join(mandatory_attrs[:])

			if optional_attrs:
				init_attrs += ", "
				init_attrs += ", ".join(map("{0}=None".format, optional_attrs))

			init = "def __init__(self, {0}):\n".format(init_attrs)
			
			for name in all_attrs:
				init += "    self.{0} = {0}\n".format(name)
			
			loc = {}
			exec compile(init, "<tempo_file_for_class_{0}>".format(name), \
						'exec') in loc
			dct['__init__'] = loc['__init__']

		return super(StructMeta, cls).__new__(cls, name, bases, dct)

class Struct(object):
	__metaclass__ = StructMeta

