import os
import re
import sys

from pygments import highlight
from pygments.lexers import PythonLexer, CLexer
from pygments.formatters import HtmlFormatter

def indent_level(line):
    line = line.replace('\t', ' ' * 4)
    return len(line) - len(line.lstrip())
    
def is_block(block):
    blines = block.split('\n')
    
    if len(blines) == 0:
        return False
        
    first_ind = indent_level(blines[0])
    
    if first_ind == 0:
        return True
        
    if len(blines) > 1 and indent_level(blines[1]) == 0:
        return True
    
    return False

header_re_sub = re.compile("(?:===+)|(?:---+)$")
def closed_block(block):
    blines = block.split('\n')
    if len(blines) == 2 and header_re_sub.match(blines[1]):
        return True
    return False

a_lot_of_line_breaks = re.compile(r"\n\n+")
def find_blocks(text):
    curr_block = []
    ntext = "\n".join([line.rstrip() for line in text.split('\n')])
    
    blocks = a_lot_of_line_breaks.split(ntext)
    rblocks = [""]
    
    for block in blocks:
        if not is_block(block) and not closed_block(rblocks[-1]):
            rblocks[-1] += '\n\n' + block
        else:
            rblocks.append(block)
    
    return rblocks

HEADER1 = 'header1'
HEADER2 = 'header2'
TEXT = 'text'
LIST = 'list'

typed_block = re.compile("([-a-zA-Z_]+):$")
typed_str = re.compile("[-a-zA-Z_]+:.*$")

def classify_block(block):
    if u'\n' not in block:
        if typed_str.match(block):
            yield block.split(':', 1)
        else:
            yield TEXT, block
    else: 
        fline, rest = block.split('\n', 1)
        mres = typed_block.match(fline)
        
        if mres is not None:
            yield mres.group(1), rest

        elif header_re_sub.match(rest):
            if rest[0] == '=':
                yield HEADER1, fline
            else:
                yield HEADER2, fline
        else:
            cblock = []
            in_list = False
            curr_indent_level = indent_level(block)
            list_items = []

            for line in block.split('\n'):
                if line.strip() == "":
                    continue
                if not in_list:
                    if line.strip().startswith('* '):
                        # we enter the first list item
                        if cblock != []:
                            yield TEXT, "\n".join(cblock)
                            cblock = []
                        in_list = True
                        curr_indent_level = indent_level(line)
                        cblock.append(line.lstrip()[2:])
                    else:
                        cblock.append(line)
                else:
                    if indent_level(line) > curr_indent_level:
                        cblock.append(line.lstrip())
                    elif indent_level(line) <= curr_indent_level:
                        # new item
                        if line.strip().startswith('* '):
                            list_items.append("\n".join(cblock))
                            cblock = [line.lstrip()[2:]]
                            curr_indent_level = indent_level(line) 
                        else:
                            # list finished
                            list_items.append("\n".join(cblock))
                            yield LIST, list_items
                            cblock = []
                            list_items = []
                            in_list = False 
            if cblock != [] or in_list:
                if in_list:
                    if cblock != []:
                        list_items.append("\n".join(cblock))
                    
                    if list_items != []:
                        yield LIST, list_items
                else:
                    if cblock != []:
                        yield TEXT, "\n".join(cblock)

def deindent_snippet(snippet):
    snippet = snippet.replace('\t', ' ' * 4)
    slines = snippet.split('\n')
    min_l_spaces = min(len(ln) - len(ln.lstrip()) for ln in slines if ln.strip() != "")
    return "\n".join(ln[min_l_spaces:] for ln in slines)

def escape_html(text, esc_all=False):
    html_escape_table = {
        "&": "&amp;",
        '"': "&quot;",
        ">": "&gt;",
        "<": "&lt;",
    }

    if esc_all:
        html_escape_table[""] = '&#39;'
    
    return "".join( html_escape_table.get(c, c) for c in text)

def highlight_python(code):
    return highlight(code, 
                    PythonLexer(), 
                    HtmlFormatter(noclasses=True))


def highlight_c(code):
    return highlight(code, 
                    CLexer(), 
                    HtmlFormatter(noclasses=True))

#re_italic = re.compile(r"(?ims)'(.*?)'")
re_bold = re.compile(r"(?ims)'(.*?)'")
re_autor = re.compile("(?ims)^:Author:.*?$")
re_href = re.compile(r"(https?://)(.*?)\s")

class NotSoRESTHandler(object):
    def __init__(self):
        self.stream = []
    
    def write(self, text):
        self.stream.append(text)
    
    def get_result(self):
        return "".join(self.stream)
    
    def process(self, tp, data):
        getattr(self, 'on_' + tp, lambda x : None)(data)


class BlogspotHTMLProvider(NotSoRESTHandler):
    def __init__(self):
        self.refs = []
        super(BlogspotHTMLProvider, self).__init__()

    def on_text(self, block, no_para=False):
        if block != "":
            if not no_para:
                self.write('<p style="text-indent:20px">')
            
            self.write(self.escape_html(block).replace('\n', ' '))
            
            if not no_para:
                self.write("</p>")
    
    def on_raw(self, block):
        self.write('<pre><font face="courier" size="">' + 
                    escape_html(block, esc_all=True) + 
                        '</font></pre>')

    def on_traceback(self, block):
        self.write('<pre><font face="courier" size="">' + 
                    escape_html(block, esc_all=True) + 
                        '</font></pre>')

    def on_python(self, block):
        self.write(highlight_python(deindent_snippet(block)).strip())
    
    def on_list(self, items):
        self.write("<ul>")
        for item in items:
            self.write("<li>")
            self.on_text(item, no_para=True)
        self.write("</ul>")

    def on_c(self, block):
        self.write(highlight_c(deindent_snippet(block)).strip())

    def on_header1(self, block):
        self.write(u"<br><h3>{0}</h3>".format(self.escape_html(block)) + '\n')

    def on_header2(self, block):
        self.write(u"<br><h4>{0}</h4>".format(self.escape_html(block)) + '\n')
    
    def process_href(self, mobj):
        g1 = mobj.group(1)
        g2 = mobj.group(2)
        self.refs.append( g1 + g2 )
        return u'<a href="{0}{1}">{1}</a><br>'.format(g1, g2)

    def escape_html(self, text):
        ntext = escape_html(text)
        ntext = re_bold.sub(ur"<b>\1</b>", ntext)
        return re_href.sub(self.process_href, ntext)


def not_so_rest_to_html(text):
    formatter = BlogspotHTMLProvider()

    for block_data in find_blocks(text.replace('\t', ' ' * 4)):
        for block_type, btext in classify_block(block_data):
            formatter.process(block_type, btext)
    
    return formatter.get_result()

def main():
    fc = open(sys.argv[1]).read().decode('utf8')
    res = not_so_rest_to_html(fc)
    res_fname = os.path.splitext(sys.argv[1])[0] + '.html'
    open(res_fname, "w").write(res.encode("utf8"))

if __name__ == "__main__":
    main()






