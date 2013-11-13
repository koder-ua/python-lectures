from oktest import ok
from nsr_lexer import *

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

test_data = { data1 : [(TEXT_H1, tuple(), "_h1_"), 
                       (TEXT_H2, tuple(), "_h2_"),
                       (TEXT_H3, tuple(), "_h3_"),
                       (TEXT_H4, tuple(), "_h4_"),
                       (TEXT_PARA, tuple(), "    MyParax\nyyyy")],
               data2 : [('raw', tuple(), "    some_data"), 
                        ('python', tuple(), "    with y:\n        pass"),
                        ('python', tuple(), "    with y:\n        pass\n\n    x = y + 1"),
                        ('Autor', tuple(), "koder"),
                        (TEXT_PARA, tuple(), "rrrr : some data")]
             }

def test():
    for bdata, data_list in test_data.items():
        for (need_tp, opts, need_data),(get_tp, get_data) in zip(data_list, parse(bdata)):
            ok(need_tp) == get_tp
            ok(need_data) == get_data

def test_lex():
    data = "python:x"
    lexems = list(lex(data))
    ok(lexems).length(1)
    ok(lexems[0]) == (BLOCK_SLINE, [], ('python', 'x'))

    data = "python[1,2]:x"
    lexems = list(lex(data))
    ok(lexems).length(1)
    ok(lexems[0]) == (BLOCK_SLINE, ['1', '2'], ('python', 'x'))

    data = "python[some_tag, ff, some_else_tag]:x"
    lexems = list(lex(data))
    ok(lexems).length(1)
    ok(lexems[0]) == (BLOCK_SLINE, ['some_tag', 'ff', 'some_else_tag'], ('python', 'x'))

    data = "python:\n    x = 1\n    y = 2"
    lexems = list(lex(data))
    ok(lexems).length(3)
    ok(lexems[0]) == (BLOCK_BEGIN, [], 'python')

    data = "python[1, some_tag, mmm ]:\n    x = 1\n    y = 2"
    lexems = list(lex(data))
    ok(lexems).length(3)
    ok(lexems[0]) == (BLOCK_BEGIN, ['1', 'some_tag', 'mmm'], 'python')

if __name__ == "__main__":
    test()
    test_lex()
