import re
from py_struct import Struct

def indent_level(line):
	return len(line) - len(line.lstrip())

block_begin_re = re.compile(r'(?P<btype>[-a-zA-Z_.]*)(?:\[(?P<opts>.*?)\])?:\s*$')
block_sline_re = re.compile(r'(?P<btype>[-a-zA-Z_.]*)(?:\[(?P<opts>.*?)\])?:\s*(?P<data>.+)$')
block_cut_re = re.compile(r'<---*>\s*$')

LINE = 'line'
BLOCK_BEGIN = 'block_begin'
DEINDENT = 'deindent'
BLOCK_SLINE = 'block_sline'
LIST_ITEM_BEGIN = 'list_item'
EMPTY_LINE = 'empty_line'

class NotSoRESTSyntaxError(ValueError):
	pass

def debug_prn(block_tp, block):
	print
	if isinstance(block, basestring):
		print block_tp 
		print
		print block.encode('utf8')
	else:
		print block_tp 
		print
		print repr(block)
	print
	print '~' * 50

def split_opts(opts):
	if opts is None:
		return {}
	else:
		res = {}
		for opt in opts.split(','):
			if '=' in opt:
				opt, val = opt.split('=', 1)
			else:
				val = True

			if opt in res:
				raise NotSoRESTSyntaxError("Myltiply opt {0!r}.")
			
			res[opt] = val

		return res

class LexLine(Struct):
	attrs = 'tp, line, opts, data[, btype]'

class LexBlock(Struct):
	attrs = 'tp, line, opts, data'

class Block(Struct):
	attrs = 'tp, line, opts, data[, style]'

def lex(fc):
	fc = fc.replace('\t', ' ' * 4)
	in_block = False

	for line_num, line in enumerate(fc.split('\n')):
		try:

			if line.strip().startswith('##'):
				continue

			if in_block:
				if line.strip() == "":
					yield LexLine(EMPTY_LINE, line_num, {}, line)
					continue
				elif indent_level(line) == 0:
					in_block = False
					yield LexLine(DEINDENT, line_num, {}, None)
					# continue execution to process current line
				else:
					yield LexLine(LINE, line_num, {}, line)
					continue

			# begin of block
			bbre = block_begin_re.match(line)

			if bbre:
				in_block = True

				opts = split_opts(bbre.group('opts'))
				yield LexLine(BLOCK_BEGIN, line_num, opts, bbre.group('btype'))
				continue

			# single line block
			bsre = block_sline_re.match(line)

			if bsre:

				opts = split_opts(bsre.group('opts'))
				yield LexLine(BLOCK_SLINE,
							  line_num, opts, 
							  bsre.group('data').strip(),
							  bsre.group('btype'))
				continue
			
			# list item begin
			if line.strip().startswith('* '):
				in_block = True
				yield LexLine(LIST_ITEM_BEGIN, line_num, {}, line[2:].strip())
				continue
			
			if line.strip() == "":
				yield LexLine(EMPTY_LINE, line_num, {}, None)
			else:
				# simple line
				yield LexLine(LINE, line_num, {}, line)
		except NotSoRESTSyntaxError as exc:
			exc.message += " In line num {0} - {1!r}".format(line_num, line)
			exc.lineno = line_num
			exc.line = line
			raise exc
		except Exception as exc:
			exc.message += "While parse line num {0} - {1!r}".format(line_num, 
															line)


LIST_ITEM = 'list_item'
TEXT_PARA = 'text'
LIST = 'list'

TEXT_H1 = 'text_h1'
TEXT_H2 = 'text_h2'
TEXT_H3 = 'text_h3'
TEXT_H4 = 'text_h4'
CUT     = 'cut'


def classify_para(data):
	"make paragraph additional classification"
	if data.count('\n') == 2:
		f, s, t = data.split('\n')

		f = f.rstrip()
		s = s.rstrip()
		t = t.rstrip()

		if len(f) == len(s) and \
		   len(s) == len(t) and \
		   len(f) == f.count('=') and \
		   len(t) == t.count('='):
			return TEXT_H1, s

	elif data.count('\n') == 1:
		f, s = data.split('\n')
		f = f.rstrip()
		s = s.rstrip()

		if len(f) == len(s):
			if len(s) == s.count('='):
				return TEXT_H2, f
			if len(s) == s.count('-'):
				return TEXT_H3, f
			if len(s) == s.count('~'):
				return TEXT_H4, f
	elif data.count('\n') == 0:
		if block_cut_re.match(data):
			return CUT, None
	return TEXT_PARA, data

def _parse(fc):
	curr_block = None
	lines_for_next_block = []

	for line in lex(fc):

		#debug_prn(line_tp, data)

		if curr_block is not None:
			if line.tp == DEINDENT:
				# fix for next problem
				# python:
				#     x = 1
				#     
				#     New text begin here with para
				# we should do......

				if len(curr_block.data) >= 3 and \
					 curr_block.data[-1] != '' and \
					 curr_block.data[-2] == '':

					lines_for_next_block = [curr_block.data[-1]]
					curr_block.data = curr_block.data[:-1]
				else:
					lines_for_next_block = []

				yield curr_block
				
				curr_block = None

			elif line.tp == LINE:
				curr_block.data.append(line.data)
			elif line.tp == EMPTY_LINE:
				# empty line is an end of paragraph
				if curr_block.tp == TEXT_PARA:

					yield curr_block
					curr_block = None

				else:
					curr_block.data.append("")
			else:
				raise NotSoRESTSyntaxError(
						("Item type {0!r} should not happened " + \
									"inside the block").format(line_tp))
		else:
			if line.tp == EMPTY_LINE:
				pass
			elif line.tp == LINE:
				curr_block = LexBlock(TEXT_PARA, line.line, line.opts, 
									  lines_for_next_block + [line.data])
				lines_for_next_block = []
			elif line.tp == BLOCK_SLINE:
				assert lines_for_next_block == []
				yield LexBlock(line.btype, line.line, line.opts, 
									  [line.data])
			elif line.tp == LIST_ITEM_BEGIN:
				curr_block = LexBlock(LIST_ITEM, 
									  line.line, 
									  line.opts, 
									  lines_for_next_block + [line.data])
				lines_for_next_block = []
			elif line.tp == BLOCK_BEGIN:
				curr_block = LexBlock(line.data, 
									  line.line + 1, 
									  line.opts, 
									  lines_for_next_block)
				lines_for_next_block = []
			else:
				raise ValueError(("Item type {0!r} should not happened " + \
									"outside the block").format(line_tp))
	
	if curr_block is not None and curr_block.data != []:
		yield curr_block

OUTPUT_TYPES = \
	[
		# BLOCK_SLINE
	    TEXT_PARA,
		LIST,
		TEXT_H1,
		TEXT_H2,
		TEXT_H3,
		TEXT_H4,
		CUT
	]

def parse(fc):
	list_items = []
	list_starts = None

	for block in _parse(fc):
		
		if len(list_items) != 0 and LIST_ITEM != block.tp:
			yield Block(LIST, list_starts, {}, list_items)
			list_items = []
			list_starts = None
		if TEXT_PARA == block.tp:
			new_tp, new_data = classify_para("\n".join(block.data))
			
			if isinstance(new_data, basestring):
				new_data = new_data.rstrip()

			yield Block(new_tp, block.line, block.opts, new_data)
		elif LIST_ITEM == block.tp:
			list_items.append("\n".join(block.data).rstrip())

			if list_starts is None:
				list_starts = block.line
		else:
			yield Block(block.tp, block.line, block.opts, 
							"\n".join(block.data).rstrip())








