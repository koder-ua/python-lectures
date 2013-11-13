import re
import sys
import ast
import inspect
import contextlib
from codegen import to_source

class VAR(object):
    def __init__(self, name):
        self.name = name
    
    def __repr__(self):
        return "VAR({0!r}, {1})".format(self.name, hex(id(self)))

class Match(object):
    def __init__(self, otype, **attrs):

        self.otype = otype
        self.attrs = {}

        name_to_var = {}
        for k,v in attrs.items():
            if isinstance(v, VAR):
                if v.name not in name_to_var:
                    name_to_var[v.name] = v
                self.attrs[k] = name_to_var[v.name]
            else:
                self.attrs[k] = v
        
    def match_val(self, obj):
        assert self.attrs == {}
        if self.otype != obj:
            return None
        else:
            return {}
    
    def __repr__(self):
        return str(self)

    def __str__(self):
        return "~{0}{1}".format(
                    self.otype.__name__,
                    ", ".join("{1}={2!r}".format(k,v) 
                        for k,v in self.attrs.items()))

    def match(self, obj):
        if not isinstance(self.otype, type):
            return self.match_val(obj)
        else:
            if not isinstance(obj, self.otype):
                return None    
            return self.match_attrs(obj)
    
    def match_attrs(self, obj):
        result = {}

        for key, val in self.attrs.items():
            try:
                rval = getattr(obj, key)
            except AttributeError:
                return None

            if isinstance(val, VAR):
                if hasattr(val, 'val'):
                    if val.val != rval:
                        return None
                result[val.name] = rval
                val.val = rval

            elif isinstance(val, Match):
                res = val.match(rval)
                if res is None:
                    return None
                
                for res_k, res_v in res.items():
                    if res_k in result:
                        if res_v != result[res_k]:
                            return None
                result.update(res)
            else:
                if isinstance(val, (tuple, list, dict, set, frozenset)):
                    if not self.match_container(val, result):
                        return None
                else:
                    if val != rval:
                        return None
            
        return result
        
    def match_container(self, val, result):
        if isinstance(val, (list, tuple)):
            # unroll/compare
            pass
        elif isinstance(val, dict):
            # dict unroll/compare
            pass
        elif isinstance(val, (set, frozenset)):
            pass
        return True


def do_match(val, otype, **attrs):
    m = Match(otype, **attrs)
    return m.match(val)

class MatchReplacer(ast.NodeTransformer):
    def visit_With(self, node):
        if isinstance(node.context_expr, ast.Call):
            obj = node.context_expr
            if isinstance(obj.func, ast.Attribute) and \
               isinstance(obj.func.value, ast.Name) and \
               obj.func.value.id == 'python_match' and \
               obj.func.attr == 'match':
                return compile_with(node)
        return node

var_re = re.compile(r"V_([\w_\d]+)$")

def is_const_node(node):
    return isinstance(node, (ast.Num, ast.Str))

def build_matcher(node, match_var):
    add_exprs = []

    if is_const_node(node):
        mval = ast.Compare(
                    left=ast.Name(id=match_var, ctx=ast.Load()), 
                    ops=[ast.Eq()], 
                    comparators=[node])
    elif isinstance(node, (ast.Name, ast.Attribute)):
        mval = ast.Call(
                        func=ast.Name(id='isinstance', ctx=ast.Load()), 
                        args=[ast.Name(id=match_var, ctx=ast.Load()), 
                              node], 
                        keywords=[], starargs=None, kwargs=None)
    elif isinstance(node, ast.Call):
        assert node.args == []
        rkeywords = []

        args = [ast.Name(id=match_var, ctx=ast.Load()), node.func]
        
        for keyword in node.keywords:
            if isinstance(keyword.value, ast.Name):
                vmatch = var_re.match(keyword.value.id)
                if vmatch:
                    var_val = ast.Call(func=ast.Attribute(
                                            value=ast.Name(id="python_match", ctx=ast.Load()),
                                            attr='VAR',
                                            ctx=ast.Load()),
                                       args=[ast.Str(vmatch.group(1))],
                                       keywords=[], starargs=None, kwargs=None)
                    rkeywords.append(ast.keyword(arg=keyword.arg, 
                                                 value=var_val))        
                    continue
            rkeywords.append(keyword)

        mval = ast.Call(
                    func=ast.Attribute(
                                value=ast.Name(id="python_match", ctx=ast.Load()),
                                attr='do_match',
                                ctx=ast.Load()), 
                    args=args, 
                    keywords=rkeywords,
                    starargs=None, kwargs=None
                    )
        
    else:
        raise ValueError("Can't make matcher from " + ast.dump(node))
    return mval

class VarTransformer(ast.NodeTransformer):
    def __init__(self, name_re, callback):
        super(VarTransformer, self).__init__()

        self.name_re = name_re
        self.callback = callback

    def visit_Name(self, node):
        rr = self.name_re.match(node.id)
        if rr:
            return self.callback(rr)
        return node

def compile_with(node):
    body = []
    matched_var_name = node.context_expr.args[0].id

    for expr in node.body:
        assert isinstance(expr.value, ast.BinOp)
        assert isinstance(expr.value.op, ast.RShift)

        processor = expr.value.right
        
        check_node = build_matcher(expr.value.left, matched_var_name)
        # val = do_match(.....)
        match_node = ast.Assign(targets=[ast.Name(id='__vals', ctx=ast.Store())],
                                  value=check_node)

        processor_call = VarTransformer(var_re, 
                                        lambda x : ast.Subscript(
                                                    value=ast.Name(id='__vals', ctx=ast.Load()), 
                                                    slice=ast.Index(value=ast.Str(s=x.group(1))), 
                                                    ctx=ast.Load())
                                        ).visit(processor)

        raise_result = ast.Raise(type=ast.Call(
                                    func=ast.Attribute(
                                            value=ast.Name(id="python_match", ctx=ast.Load()),
                                            attr='Value',
                                            ctx=ast.Load()), 
                                    args=[processor_call],
                                    keywords=[], starargs=None, kwargs=None),
                                inst=None, tback=None
                                )
        
        
        if_node = ast.If(test=ast.Compare(
                                  left=ast.Name(id='__vals', ctx=ast.Load()), 
                                   ops=[ast.NotIn()],
                                  comparators=[ast.Tuple(
                                      elts=[ast.Name(id='None', ctx=ast.Load()), 
                                            ast.Name(id='False', ctx=ast.Load())], 
                                            ctx=ast.Load())]                                    
                                   ), 
                         body=[raise_result], 
                         orelse=[])
        
        for new_node in (match_node, if_node):
            ast.copy_location(new_node, expr)
            ast.fix_missing_locations(new_node)
            body.append(new_node)
    
    node_body = ast.Call(
                    func=ast.Attribute(
                                value=ast.Name(id="python_match", ctx=ast.Load()),
                                attr='marked_match__',
                                ctx=ast.Load()), 
                    args=node.context_expr.args, 
                    keywords=node.context_expr.keywords,
                    starargs=node.context_expr.starargs, 
                    kwargs=node.context_expr.kwargs
                    )

    new_node = ast.With(body=body,
                    context_expr=node_body,
                    optional_vars=node.optional_vars)

    ast.copy_location(new_node, node)
    ast.fix_missing_locations(new_node)

    #print ast.dump(node)
    return new_node

class Value(Exception):
    def __init__(self, val):
        self.val = val

def update(func):
    func_ast = ast.parse(inspect.getsource(func).split("\n", 1)[1])
    new_func = MatchReplacer().visit(func_ast)
    #print to_source(new_func)
    code = compile(new_func, inspect.getfile(func), 'exec')
    fr = sys._getframe(1)
    l = fr.f_locals
    g = fr.f_globals
    eval(code, g, l)
    return l[func.__name__]

def match(x):
    raise RuntimeError("Function, which use match should be decorated with update")

class Res(object):
    pass

@contextlib.contextmanager
def marked_match__(val):
    try:
        res = Res()
        yield res
    except Value as val:
        res.res = val.val
    else:
        raise ValueError("Can't found approprite match for {0!r}".format(val))
    
