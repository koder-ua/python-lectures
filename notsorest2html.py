# -*- coding:utf8 -*-

import os
import re
import sys

from pygments import highlight
from pygments.lexers import PythonLexer, \
                            CLexer, \
                            XmlLexer, \
                            PythonTracebackLexer, \
                            PythonConsoleLexer

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
    block = block.lstrip()
    if u'\n' not in block:
        if typed_str.match(block):
            yield block.split(':', 1)
        elif block.startswith('* '):
            yield LIST, [block[2:   ]]
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


#re_italic = re.compile(r"(?ims)'(.*?)'")
re_bold = re.compile(r"(?ims)'(.*?)'")
re_autor = re.compile("(?ims)^:Author:.*?$")
re_href = re.compile(r"(?P<name>\[.*?\])?(?P<proto>https?://)(?P<url>.*?)(?=\s|$)")

class NotSoRESTHandler(object):
    def __init__(self):
        self.stream = []
    
    def write(self, text):
        self.stream.append(text)
    
    def get_result(self):
        return "".join(self.stream)
    
    def process(self, tp, data, style):
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

    highlighters_map = {}
    highlighters_map['python'] = PythonLexer
    highlighters_map['c'] = CLexer
    highlighters_map['xml'] = XmlLexer
    highlighters_map['traceback'] = PythonTracebackLexer
    highlighters_map['pyconsole'] = PythonConsoleLexer

    def getattr(self, name):
        # handle all syntax hightlited blocks
        if name.startswith('on_'):
            block = name[3:]
            if block in self.highlighters_map:
                lexer = self.highlighters_map[block]
                def hliter(code):
                    code = deindent_snippet(code)
                    hblock = highlight(code, lexer, HtmlFormatter(noclasses=True))
                    self.write(code.strip())
                return hliter
        raise AttributeError("type %r has no attribute %s" % (self.__class__, name))
                
    def on_img(self, url):
        url = url.strip()
        if url.endswith('svg'):
            self.write('<object data="{0}" type="image/svg+xml"></object>'.format(url)) 
        else:
            self.write('<br><img src="{0}" width="740" /><br>'.format(url))

    def on_linklist(self, block):
        self.write(u"Ccылки:<br>")
        for line in block.split('\n'):
            line = line.strip()
            self.do_href(line)
            self.write("<br>")

    def do_href(self, ref_descr):        
        self.write(self.process_href(re_href.match(ref_descr))) 
               
    def on_list(self, items):
        self.write("<ul>")
        for item in items:
            self.write("<li>")
            self.on_text(item, no_para=True)
        self.write("</ul>")

    def on_header1(self, block):
        self.write(u"<br><h3>{0}</h3>".format(self.escape_html(block)) + '\n')

    def on_header2(self, block):
        self.write(u"<br><h4>{0}</h4>".format(self.escape_html(block)) + '\n')
    
    def process_href(self, mobj):
        g1 = mobj.group('proto')
        g2 = mobj.group('url')
        name = mobj.group('name')

        if g2[-1] in '.,':
            add_symbol = g2[-1]
            g2 = g2[:-1]
        else:
            add_symbol = ""

        if not name:
            name = g2
        else:
            name = name[1:-1]

        #print repr(g1), repr(g2), repr(name), repr(add_symbol)

        url = g1 + g2
        self.refs.append( url )
        
        return u'<a href="{0}">{1}</a>{2}'.format(url, name, add_symbol)

    def escape_html(self, text):
        ntext = escape_html(text)
        ntext = re_bold.sub(ur"<b>\1</b>", ntext)
        return re_href.sub(self.process_href, ntext)
    
    def write_footer(self):
        self.write(u'Исходники этого и других постов со скриптами лежат тут - ')
        self.do_href("[github.com/koder-ua]https://github.com/koder-ua/python-lectures.")
        self.write(u'При использовании их, пожалуйста, ссылайтесь на ')
        self.do_href("[koder-ua.blogspot.com]http://koder-ua.blogspot.com/.")
 

def not_so_rest_to_html(text, styles):
    formatter = BlogspotHTMLProvider()

    text = text.replace('\t', ' ' * 4)
    # skip header
    text = text.split('\n', 3)[3]

    for block_data in find_blocks(text):
        for block_type, btext in classify_block(block_data):

            if block_type in styles:
                block_type, style = styles[block_type]
            else:
                style = None

            formatter.process(block_type, btext, style)
    
    formatter.write_footer()
    return formatter.get_result()

style_cmd_re = re.compile(r"(?P<new_style>[-a-zA-Z0-9_]*)\s*=\s*(?P<old_style>[-a-zA-Z0-9_]*)\s*\[(?P<opts>.*)\]\s*(?:#.*)?$")

def parse_style_file(fname):
    res = {}
    for lnum, line in enumerate(open(fname).readlines()):
        line = line.strip()

        if line.startswith('#'):
            continue
        
        mres = style_cmd_re.match(line)
        if not mres:
            raise RuntimeError("Error in style file {0!r} in line {1}".format(fname, lnum))
        
        opts = {}
        for opt in mres.group('opts').split(','):
            opt = opt.strip()
            name, val = opt.split('=', 1)
            opts[name] = val
        
        res[mres.group('new_style')] = (mres.group('old_style'), opts)
    return res


def main(argv=None):
    import optparse

    argv = argv or sys.argv
    
    parser = optparse.OptionParser()

    parser.add_option("-s", "--style-files", dest='style_files', default='')
    parser.add_option("-o", "--output-file", dest='output_file', default=None)
    parser.add_option("-f", "--format", dest='format', default='html')
    
    opts, files = parser.parse_args(argv)

    if len(files) < 2:
        print "Error - no template files"

    if len(files) > 2:
        print "Error - only one template file per call allowed"
    
    fname = files[0]
    fc = open(fname).read().decode('utf8')
    
    styles = {}
    # {new_style : (old_style, {param:val})}
    if opts.style_files != '':
        for style_fname in opts.style_files.split(':'):
            styles.update(parse_style_file(style_fname))

    if opts.format == 'html':
        res = not_so_rest_to_html(fc, styles)
    else:
        print "Unknown format " + repr(opts.format)
    
    if opts.output_file is None:
        res_fname = os.path.splitext(fname)[0] + '.html'
    else:
        res_fname = opts.output_file

    open(res_fname, "w").write(res.encode("utf8"))

if __name__ == "__main__":
    main()






