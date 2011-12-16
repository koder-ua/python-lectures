import re

def indent_level(line):
	return len(line) - len(line.lstrip())

block_begin_re = re.compile(r'(?P<btype>[-a-zA-Z_]*)(?:\[(?P<opts>.*?)\])?:\s*$')
block_sline_re = re.compile(r'(?P<btype>[-a-zA-Z_]*)(?:\[(?P<opts>.*?)\])?:\s*(?P<data>.+)$')
block_cut_re = re.compile(r'<---*>\s*$')

LINE = 'line'
BLOCK_BEGIN = 'block_begin'
DEINDENT = 'deindent'
BLOCK_SLINE = 'block_sline'
LIST_ITEM_BEGIN = 'list_item'
EMPTY_LINE = 'empty_line'

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
		return []
	else:
		return [i.strip() for i in opts.split(',')]

def lex(fc):
	fc = fc.replace('\t', ' ' * 4)
	in_block = False

	for line in fc.split('\n'):
		
		if line.strip().startswith('##'):
			continue

		if in_block:
			if line.strip() == "":
				yield EMPTY_LINE, None, line
				continue
			elif indent_level(line) == 0:
				in_block = False
				yield DEINDENT, None, None
				# continue execution to process current line
			else:
				yield LINE, None, line
				continue

		# begin of block
		bbre = block_begin_re.match(line)

		if bbre:
			in_block = True

			opts = split_opts(bbre.group('opts'))
			yield BLOCK_BEGIN, opts, bbre.group('btype')
			continue

		# single line block
		bsre = block_sline_re.match(line)

		if bsre:

			opts = split_opts(bsre.group('opts'))
			yield BLOCK_SLINE, opts, (bsre.group('btype'), 
									  bsre.group('data').strip())
			continue
		
		# list item begin
		if line.strip().startswith('* '):
			in_block = True
			yield LIST_ITEM_BEGIN, None, line[2:].strip()
			continue
		
		if line.strip() == "":
			yield EMPTY_LINE, None, None
		else:
			# simple line
			yield LINE, None, line

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
	in_block = False
	cblock = []
	block_tp = None

	for line_tp, opts, data in lex(fc):

		#debug_prn(line_tp, data)

		if in_block:
			if line_tp == DEINDENT:
				# fix for next problem
				# python:
				#     x = 1
				#     
				#     New text begin here with para
				# we should do......

				if len(cblock) >= 3 and cblock[-1] != '' and cblock[-2] == '':
					not_a_block_line = cblock[-1]
					cblock = cblock[:-1]
				else:
					not_a_block_line = None

				yield block_tp, "\n".join(cblock)

				if not_a_block_line:
					cblock = [not_a_block_line]
				else:
					cblock = []
				
				in_block = False
				block_tp = None
			elif line_tp == LINE:
				cblock.append(data)
			elif line_tp == EMPTY_LINE:
				# empty line is an end of paragraph
				if block_tp == TEXT_PARA:
					yield block_tp, "\n".join(cblock) 
					cblock = []
					in_block = False
					block_tp = None
				else:
					cblock.append("")
			else:
				raise ValueError("Item type {0!r} should not happened inside the block".format(line_tp))
		else:
			if line_tp == EMPTY_LINE:
				pass
			elif line_tp == LINE:
				block_tp = TEXT_PARA
				in_block = True
				cblock.append(data)
			elif line_tp == BLOCK_SLINE:
				block_tp, data = data
				yield block_tp, data
			elif line_tp == LIST_ITEM_BEGIN:
				block_tp = LIST_ITEM
				in_block = True
				cblock.append(data)
			elif line_tp == BLOCK_BEGIN:
				block_tp = data
				in_block = True
			else:
				raise ValueError("Item type {0!r} should not happened outside the block".format(line_tp))
	
	if in_block and cblock != []:
		yield block_tp, "\n".join(cblock)

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

	for block_tp, block in _parse(fc):
		
		if len(list_items) != 0 and LIST_ITEM != block_tp:
			yield LIST, list_items
			list_items = []
		if TEXT_PARA == block_tp:
			new_tp, new_data = classify_para(block)
			if isinstance(new_data, basestring):
				new_data = new_data.rstrip()
			yield new_tp, new_data
		elif LIST_ITEM == block_tp:
			list_items.append(block.rstrip())
		else:
			yield block_tp, block.rstrip()








