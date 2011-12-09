import re

def indent_level(line):
	return len(line) - len(line.lstrip())

block_begin_re = re.compile(r'([a-zA-Z]*):\s*$')
block_sline_re = re.compile(r'([a-zA-Z]*):\s*(.*)$')

LINE = 'line'
BLOCK_BEGIN = 'block_begin'
BLOCK_END = 'block_end'
BLOCK_SLINE = 'block_sline'
LIST_ITEM_BEGIN = 'list_item'
EMPTY_LINE = 'empty_line'

def lex(fc):
	fc = fc.replace('\t', ' ' * 4)
	in_block = False
	block_indent = None

	for line in fc.split('\n'):
		if in_block:
			if line.strip() == "":
				yield EMPTY_LINE, line
				continue
			elif indent_level(line) <= block_indent:
				in_block = False
				yield BLOCK_END, None
				# continue execution to process current line
			else:
				yield LINE, line
				continue

		# begin of block
		bbre = block_begin_re.match(line)

		if bbre:
			block_indent = indent_level(line)
			in_block = True
			yield BLOCK_BEGIN, bbre.group(1)
			continue

		# single line block
		bsre = block_sline_re.match(line)

		if bsre:
			yield BLOCK_SLINE, (bsre.group(1), bsre.group(2).strip())
			continue
		
		# list item begin
		if line.strip().startswith('* '):
			block_indent = indent_level(line)
			in_block = True
			yield LIST_ITEM_BEGIN, line[2:].strip()
			continue
		
		if line.strip() == "":
			yield EMPTY_LINE, None
		else:
			# simple line
			yield LINE, line

LIST_ITEM = 'list_item'
TEXT_PARA = 'text_para'
LIST = 'list'

TEXT_H1 = 'text_h1'
TEXT_H2 = 'text_h2'
TEXT_H3 = 'text_h3'
TEXT_H4 = 'text_h4'


def classify_para(data):
	"make paragraph additional classification"
	if data.count('\n') == 2:
		f, s, t = data.split('\n')
		if len(f) == len(s) and \
		   len(s) == len(t) and \
		   len(f) == f.count('=') and \
		   len(t) == t.count('='):
			return TEXT_H1, s

	elif data.count('\n') == 1:
		f, s = data.split('\n')
		if len(f) == len(s):
			if len(s) == s.count('='):
				return TEXT_H2, f
			if len(s) == s.count('-'):
				return TEXT_H3, f
			if len(s) == s.count('~'):
				return TEXT_H4, f
	return TEXT_PARA, data

def _parse(fc):
	in_block = False
	cblock = []
	block_tp = None

	for line_tp, data in lex(fc):
		
		if in_block:
			if line_tp == BLOCK_END:
				yield block_tp, "\n".join(cblock)
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
				cblock = [data]
			elif line_tp == BLOCK_SLINE:
				block_tp, data = data
				yield block_tp, data
			elif line_tp == LIST_ITEM_BEGIN:
				block_tp = LIST_ITEM
				in_block = True
				cblock = [data]
			elif line_tp == BLOCK_BEGIN:
				block_tp = data
				in_block = True
				cblock = []
			else:
				raise ValueError("Item type {0!r} should not happened outside the block".format(line_tp))
	
	if in_block and cblock != []:
		yield block_tp, "\n".join(cblock)

def parse(fc):
	list_items = []

	for block_tp, block in _parse(fc):
		if len(list_items) != 0 and LIST_ITEM != block_tp:
			yield LIST, list_items
			list_items = []
		if TEXT_PARA == block_tp:
			new_tp, new_data = classify_para(block)
			yield new_tp, new_data.rstrip()
		elif LIST_ITEM == block_tp:
			list_items.append(block.rstrip())
		else:
			yield block_tp, block.rstrip()
	 
data1 = \
"""
====
_h1_
====

_h2_
====

_h3_
----

_h4_
~~~~

	MyParax
yyyy

"""

data2 = \
"""
raw:
	some_data

python:
	with y:
		pass

python:
	with y:
		pass

	x = y + 1

Autor: koder

rrrr : some data
"""

data3 = \
"""
Some text:
	* X1
	* X2
	* X3
"""

test_data = { data1 : [(TEXT_H1,"_h1_"), 
					   (TEXT_H2,"_h2_"),
					   (TEXT_H3,"_h3_"),
					   (TEXT_H4,"_h4_"),
					   (TEXT_PARA, "    MyParax\nyyyy")],
			   data2 : [('raw',"    some_data"), 
			 		   ('python',"    with y:\n        pass"),
			 		   ('python',"    with y:\n        pass\n\n    x = y + 1"),
			 		   ('Autor', "koder"),
			 		   (TEXT_PARA, "rrrr : some data")]
			 }

def test():
	from oktest import ok

	for bdata, data_list in test_data.items():
		for (need_tp, need_data),(get_tp, get_data) in zip(data_list, parse(bdata)):
			ok(need_tp) == get_tp
			ok(need_data) == get_data

if __name__ == "__main__":
	test()

			












