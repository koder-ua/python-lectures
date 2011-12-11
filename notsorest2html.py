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

from nsr_lexer import parse


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
        html_escape_table["'"] = '&#39;'
    
    return "".join( html_escape_table.get(c, c) for c in text)


re_bold1    = re.compile(r"(?i)(?<=\W)'\b(.+?)\b'(?=\W|$)")
re_it1      = re.compile(r"(?i)(?<=\W)\*\b(.+?)\b\*(?=\W|$)")
re_striked1 = re.compile(r"(?i)(?<=\W)-\b(.+?)\b-(?=\W|$)")

re_bold2    = re.compile(r"(?i)^'\b(.+?)\b'(?=\W|$)")
re_it2      = re.compile(r"(?i)^\*\b(.+?)\b\*(?=\W|$)")
re_striked2 = re.compile(r"(?i)^-\b(.+?)\b-(?=\W|$)")

assert not re_striked1.search('a-b-c')
assert not re_striked1.search('a-b-')
assert re_striked2.match('-b-')
assert re_striked1.search(' -b-')
assert re_striked1.search(' -b- ')

re_backref = re.compile(r"\[\s*([- _a-zA-Z]+)\s*\]")
re_href = re.compile(r"(?P<name>\[\s*([- _a-zA-Z/.]+)\s*\])?(?P<proto>https?://)(?P<url>.*?)(?=\s|$)")

class NotSoRESTHandler(object):
    def __init__(self):
        self.stream = []
    
    def write_raw(self, text):
        self.stream.append(text)
    
    def get_result(self):
        return "".join(self.stream)
    
    def process(self, tp, data, style):

        if style is not None:
            self.start_style(style)

        getattr(self, 'on_' + tp)(data) #, lambda x : None

        if style is not None:
            self.end_style(style)


class BlogspotHTMLProvider(NotSoRESTHandler):
    def __init__(self):
        self.refs = []
        super(BlogspotHTMLProvider, self).__init__()

    def write_text(self, text):
        self.write_raw(self.text_to_html(text).replace('\n', ' '))

    def text_to_html(self, text):
        
        ntext = escape_html(text)
        
        ntext = re_bold1.sub(r"<b>\1</b>", ntext)
        ntext = re_it1.sub(r"<i>\1</i>", ntext)
        ntext = re_striked1.sub(r"<s>\1</s>", ntext)
        ntext = re_bold2.sub(r"<b>\1</b>", ntext)
        ntext = re_it2.sub(r"<i>\1</i>", ntext)
        ntext = re_striked2.sub(r"<s>\1</s>", ntext)
        ntext = re_backref.sub(self.process_backref, ntext)
        ntext = re_href.sub(self.process_href, ntext)

        return ntext
    
    def start_style(self, style):
        self.write_raw('<span style="{0}">'.format(style))
    
    def end_style(self, style):
        self.write_raw('</span>')

    def on_text(self, block, no_para=False):
        if block != "":
            if not no_para:
                self.write_raw('<p style="text-indent:20px">')
            
            self.write_text(block)
            
            if not no_para:
                self.write_raw("</p>")
    
    def on_cut(self, block):
        self.write_raw("<!--more-->")

    def on_raw(self, block):
        self.write_raw('<pre><font face="courier">' + 
                       escape_html(block, esc_all=True) + 
                        '</font></pre>')

    highlighters_map = {}
    highlighters_map['python'] = PythonLexer
    highlighters_map['c'] = CLexer
    highlighters_map['xml'] = XmlLexer
    highlighters_map['traceback'] = PythonTracebackLexer
    highlighters_map['pyconsole'] = PythonConsoleLexer

    def __getattr__(self, name):
        # handle all syntax hightlited blocks
        if name.startswith('on_'):
            block = name[3:]
            if block in self.highlighters_map:
                lexer = self.highlighters_map[block]
                def hliter(code):
                    code = deindent_snippet(code)
                    hblock = highlight(code, lexer(), HtmlFormatter(noclasses=True))
                    self.write_raw(hblock.strip())
                return hliter

        if name in ('on_text_h2', 'on_text_h3', 'on_text_h4'):
            def header(text):
                hlevel = int(name[-1])
                self.write_raw('<br><h{0}>'.format(hlevel))
                self.write_text(text)
                self.write_raw('</h{0}>'.format(hlevel))
            return header

        raise AttributeError("type %r has no attribute %s" % (self.__class__, name))

    def on_text_h1(self, text):
        # skip main header for blogspot
        pass

    def on_img(self, url):
        url = url.strip()
        if url.endswith('svg'):
            self.write_raw('<object data="{0}" type="image/svg+xml"></object>'.format(url)) 
        else:
            self.write_raw('<br><img src="{0}" width="740" /><br>'.format(url))

    def do_href(self, ref_descr):        
        self.write_raw(
            self.process_href(
                re_href.match(ref_descr))) 
    
    def on_list(self, items):
        
        self.write_raw("<ul>")
        for item in items:
            self.write_raw("<li>")
            self.on_text(item, no_para=True)
        self.write_raw("</ul>")
    
    def on_linklist(self, block):
        self.on_text(u"Ссылки:", no_para=True)
        self.write_raw("<br>")

        for line in block.split('\n'):
            line = line.strip()
            
            if line == "":
                continue

            if 'http://' in line:
                name, url = line.split('http://', 1)
                name = name.strip()
                url = "http://" + url
            elif 'https://' in line:
                name, url = line.split('https://', 1)
                name = name.strip()
                url = "https://" + url
            else:
                raise ValueError("Can't process linklist item {0!r}".format(line))
            
            self.write_raw('&nbsp;' * 10)
            if name:
                self.write_raw('<a name="{0}">'.format(
                    escape_html(name.replace(' ', '_'))))

            self.do_href(url)

            if name:
                self.write_raw('</a>')
            
            self.write_raw('<br>')

    def process_backref(self, ref_descr):
        gr1 = ref_descr.group(1)
        return '<a href="#{0}">{1}</a>'.format(
                    escape_html(gr1.replace(' ', '_')), 
                    escape_html(gr1))
               
    def process_href(self, mobj):
        name = mobj.group('name')
        g1 = mobj.group('proto')
        g2 = mobj.group('url')

        if g2[-1] in '.,':
            add_symbol = g2[-1]
            g2 = g2[:-1]
        else:
            add_symbol = ""
        
        if name is None:
            name = g2
        else:
            name = name[1:-1]

        url = g1 + g2
        self.refs.append( url )
        
        return u'<a href="{0}">{1}</a>{2}'.format(url, name, add_symbol)

    def write_footer(self):
        self.write_raw(u'Исходники этого и других постов со скриптами лежат тут - ')
        self.do_href("[github.com/koder-ua]https://github.com/koder-ua/python-lectures.")
        self.write_raw(u'При использовании их, пожалуйста, ссылайтесь на ')
        self.do_href("[koder-ua.blogspot.com]http://koder-ua.blogspot.com/.")
 

def debug_block(block_type, data):
    print block_type 
    print 
    if isinstance(data, basestring):
        print data.encode('utf8')
    elif isinstance(data, (list, tuple)):
        print (u"\n >>>> " + u"\n >>>> ".join(data)).encode('utf8')
    else:
        print repr(data)

    print "~~" * 50
    print

def not_so_rest_to_xxx(text, styles, formatter):

    text = text.replace('\t', ' ' * 4)
    
    # skip header
    text = text.split('\n', 3)[3]

    for block_type, data in parse(text):
        
        #debug_block(block_type, data)

        if block_type in styles:
             block_type, style = styles[block_type]
        else:
             style = None

        formatter.process(block_type, data, style)
    
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
        
        res[mres.group('new_style')] = (mres.group('old_style'), mres.group('opts'))
    return res


def main(argv=None):
    import optparse

    argv = argv or sys.argv
    
    parser = optparse.OptionParser()

    parser.add_option("-s", "--style-files", dest='style_files', default='notsores_styles.txt')
    parser.add_option("-o", "--output-file", dest='output_file', default=None)
    parser.add_option("-f", "--format", dest='format', default='blogspot')
    
    opts, files = parser.parse_args(argv)

    if len(files) < 2:
        print "Error - no template files"
        return 1

    if len(files) > 2:
        print "Error - only one template file per call allowed"
        return 1
    
    fname = files[1]
    fc = open(fname).read().decode('utf8')
    
    styles = {}

    # {new_style : (old_style, css)}

    if opts.style_files != '':
        for style_fname in opts.style_files.split(':'):
            styles.update(parse_style_file(style_fname))

    formatters = {
        'blogspot' : BlogspotHTMLProvider()
    }

    if opts.format not in formatters:
        print >>sys.stderr, "Unknown format {0!r} only '{1}'' formats are supported"\
                    .format(opts.format, ",".join(formatters.keys()))
        return 1
    else:
        res = not_so_rest_to_xxx(fc, styles, formatters[opts.format])
    
        if opts.output_file is None:
            res_fname = os.path.splitext(fname)[0] + '.html'
        else:
            res_fname = opts.output_file

        open(res_fname, "w").write(res.encode("utf8"))
        return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))






