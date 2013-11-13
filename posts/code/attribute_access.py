import sys
import time
import timeit

NUM = 1024 #1

prep = """
class WithGetattribute(object):
    def __getattribute__(self, name):
        return None

w_getattribute = WithGetattribute()

class WithGetattr(object):
    def __getattr__(self, name):
        return None

w_getattr = WithGetattr()

class DProp(object):
    def a_get(self):
        return None

    def a_set(self):
        pass
    
    a = property(a_get, a_set)

d_prop = DProp()

class Prop(object):
    def a_get(self):
        return None
    a = property(a_get)

prop = Prop()

class Test(object):
    pass

def get_nested_attr_obj(nested_level):
    robj = Test()
    obj = robj
    for _ in range(nested_level):
        obj.attr = Test()
        obj = obj.attr
    return robj

def get_nested_attr_class(nested_level):
    curr = object
    for num in range(nested_level)[::-1]:
        curr = type("Ctest", (curr,), {"attr{0}".format(num):None}) 
    return curr

a = get_nested_attr_obj(128)
c = get_nested_attr_class(128)

def func_empty():
    pass

def func_zero(x = 1):
    y = 1
"""
#----------------------------------------------------------------------------------
attr_access = {}
for num in (1, 2, 4, 16, 32, 64, 128):
    attr_access[num] = "a" + '.attr' * num

cattr1 = "c.attr0"
cattr127 = "c.attr127"
#----------------------------------------------------------------------------------
func_param_prep = """
def func_param(x = 1):
    y = 1
""" + "    x\n"   * NUM
func_param_work = "func_param()"
#----------------------------------------------------------------------------------
func_local_prep = """
def func_local(x = 1):
    y = 1
""" + "    y\n"   * NUM
func_local_work = "func_local()"
#----------------------------------------------------------------------------------
func_global_prep = """
y = 1
def func_global(x = 1):
    x = 1
""" + "    y\n"  * NUM
func_global_work = "func_global()"
#----------------------------------------------------------------------------------
class TipaCenter(object):
    def __init__(self):
        self.sz = None 
    def __mod__(self, sz):
        if self.sz is None:
            self.sz = sz
            return self
        else:
            return sz.center(self.sz)

class Formatter(object):
    @staticmethod
    def center_dot(val, coef, after_dot=1):
        val *= coef
        v1 = int(val)
        v2 = int((val - v1) * (10 ** after_dot))
        return "{0}.{1!s:>0{2}}".format(v1, v2, after_dot)
    
    @staticmethod
    def select_scale(val, scales):
        if val < 0:
            val = -val
            sign = '-'
        else:
            sign = ''
        
        for units, coef in scales:
            if val * coef > 100.0:
                return "{2}{0}{1}".format(int(val * coef), units, sign)
            elif val * coef > 10.0:
                return "{2}{0:.1f}{1}".format(val * coef, units, sign)
            if val * coef > 1.0:
                return "{2}{0:.2f}{1}".format(val * coef, units, sign)
        
        return "{0:.2e}".format(val)

    @staticmethod
    def scales(name):
        iscales = ((''  , 1), 
                   ('m' , 1000), 
                   ('mk', 1000 * 1000),
                   ('n' , 1000 * 1000 * 1000),
                   ('p' , 1000 * 1000 * 1000 * 1000),
                   ('f' , 1000 * 1000 * 1000 * 1000 * 1000))
        for pref, scale in iscales:
            yield pref + name, scale

    @classmethod
    def to_time(cls, val):
        return cls.select_scale(val, cls.scales('s'))
    
    @classmethod
    def format_func(cls, formats):
        "helper for print_table"

        def closure(name, val):
            "closure"

            frmt = formats.get(name, "%s")
            #print name, "->", frmt, val
            if isinstance(frmt, str):
                return frmt % (val, )
            return frmt(val)
        return closure

    @classmethod
    def format_table(cls, table, names, formats=None, allign=None):
        """pretty-print for tables"""

        max_column_sizes = [0] * len(names)
        ffunc = cls.format_func(formats or {})

        for pos, val in enumerate(names):
            max_column_sizes[pos] = max(max_column_sizes[pos], len(val))

        for line in table:
            for pos, val in enumerate(line):
                max_column_sizes[pos] = max(max_column_sizes[pos],
                                            len(ffunc(names[pos], val)))

        super_formats = []

        for pos, size in enumerate(max_column_sizes):           
            if allign is None:
                sft = "%%-%ss"
            elif allign[pos] == '<':
                sft = "%%-%ss"
            elif allign[pos] == '>':
                sft = "%%%ss"
            elif allign[pos] == 'c':
                sft = TipaCenter()

            super_formats.append(sft % size)

        sep = '-' + '-' * (sum(max_column_sizes) + (len(names) - 1) * 3) + '-'

        res = []
        res.append( "\n+" + sep + "+\n")

        line = []
        for frmt, name  in zip(super_formats, names):
            line.append(frmt % name)

        res.append("| " + " | ".join(line) + " |")

        res.append( "\n|" + sep + "|\n")

        for line in table:
            res_line = []
            for frmt, name, val in zip(super_formats, names, line):
                res_line.append(frmt % (ffunc(name, val)))
            res.append("| " + " | ".join(res_line) + " |\n")

        res.append("+" + sep + "+\n")

        return "".join(res)

class ADVTimeit(object):
    
    TIMEIT_TIME = 1
    NUM_CALLS_TO_DELTA = 1

    timeit_overhead = None

    def __init__(self, timer=time.time, exp_time=None, num_call_cycles=None ):
        self.timer = timer

        if exp_time is None:
            exp_time = self.TIMEIT_TIME
        self.exp_time = float(exp_time)
    
        if num_call_cycles is None:
            num_call_cycles = self.NUM_CALLS_TO_DELTA
        self.num_call_cycles = num_call_cycles

        #self.find_timeit_overhead()

    def find_timeit_overhead(self):
        if self.timeit_overhead is None:
            number = 1000 * 1000 * 1000
            self.__class__.timeit_overhead = timeit.timeit('pass', '',
                                                            number=number, 
                                                            timer=self.timer) / number
            sys.stdout.write("self.timeit_overhead =" + str(self.timeit_overhead) + '\n')

    def timeit(self, work, prep, number=None):
        number = 1
        t = timeit.timeit(work, prep, number=number, timer=self.timer)

        while t < self.exp_time * 0.01:
            number *= 10
            t = timeit.timeit(work, prep, number=number, timer=self.timer)

        number *= self.exp_time / t
        number = int(number)
        t = timeit.timeit(work, prep, number=number, timer=self.timer)
        
        if self.timeit_overhead is not None:
            return t / number - self.timeit_overhead
        else:
            return t / number

    def timeit_with_stat(self, work, prep):
        times = []

        for _ in range(self.num_call_cycles):
            times.append(self.timeit(work, prep))
        
        times.sort()

        drop = int(round(self.num_call_cycles * 0.1))
        
        while drop * 2 >= len(times):
            drop -= 1
        
        if drop != 0:
            times = times[drop:-drop]

        mid_time = sum(times) / len(times)
        delta = max(mid_time - times[0], times[-1] - mid_time)

        return mid_time, delta

    def timeit_range_scan(self, work, prep, max_sz=14):

        times = []

        for i in range(max_sz):
            number = 2 ** i
            if number > 1:
                cwork = (work + ';' ) * number
            else:
                cwork = work
            yield number, self.timeit(cwork, prep) / number
        
        #print "{0:>2} => {1:.2e}".format(i, tm)

def get_time(work, prep, num1=1, num2=None, zero=0):
    atime = ADVTimeit()

    if num1 > 1:
        work = (work + ';') * num1
    
    tm, diff = atime.timeit_with_stat(work, prep)

    tm -= zero

    if num2 is None:
        tm /= num1
        diff /= num1
    else:
        tm /= num2
        diff /= num2

    return tm, diff

def show_time(msg, work, prep, num1=1, num2=None, zero=0):
    tm, diff = get_time(work, prep, num1, num2, zero)
    print "{0:.1e}".format(tm )
    sys.stdout.write("{0:<25} => {1:>6} {2}%\n".format(msg,
                               Formatter.center_dot(tm, 1000 * 1000 * 1000),
                               int((diff / tm) * 100)))

def range_scan(work, prep):
    scanner = ADVTimeit(exp_time=1)
    for num, tm in scanner.timeit_range_scan(work, prep):
        sys.stdout.write("{0:>6} => {1:>8}\n".format(num, Formatter.to_time(tm)))

class TimeMe(object):
    def __init__(self, msg, work, prep, num1=1, num2=None, zero=0):
        self.work = work
        self.prep = prep
        self.num1 = num1
        self.num2 = num2
        self.zero = zero
        self.msg  = msg
        self.tm = None
        self.diff = None
    
    def get_time(self):
        self.tm, diff = get_time(self.work, self.prep, self.num1, self.num2, self.zero)
        self.diff = diff / self.tm
        return self

def main():
    var = TimeMe("Global var access", "x", "x=1", NUM)
    empty_func = TimeMe("Empty func call", "func_empty()", prep, NUM)
    zero_func = TimeMe("", "func_zero()", prep, NUM)
    zero_func.get_time()
    zero = zero_func.tm

    func_glob_var = TimeMe("Global var from func", func_global_work, func_global_prep, num2=NUM, zero=zero)
    func_local_var = TimeMe("Local var from func", func_local_work, func_local_prep, num2=NUM, zero=zero)
    int_plus_int = TimeMe("int + int", "a + b", "a=1;b=1",  NUM)
    getattribute = TimeMe("A.__getattribute__(a, 'b')", "w_getattribute.x", prep, NUM)
    data_prop = TimeMe("A.b.__get__(a) data property", "d_prop.a", prep,  NUM)
    from_obj_dict = TimeMe("a.__dict__['b']", attr_access[1], prep, NUM)
    prop = TimeMe("A.b.__get__(a) property", "prop.a ", prep,  NUM)
    cattr1_time = TimeMe("A.__dict__['b'] with deep " + cattr1, cattr1, prep, NUM)
    cattr127_time = TimeMe("A.__dict__['b'] with deep " + cattr127, cattr127, prep, NUM)
    getattr_tm = TimeMe("A.__getattr__(a, 'b')", "w_getattr.x", prep, NUM)
    attr2_tm = TimeMe("a.b.b", attr_access[2], prep, NUM)
    attr4_tm = TimeMe("a.b.b.b.b", attr_access[4], prep, NUM)
    attr128_tm = TimeMe("a....b (128)", attr_access[128], prep, NUM)

    all_list = [var, empty_func, func_glob_var, func_local_var, int_plus_int]#, getattribute, data_prop, 
                #from_obj_dict, prop, cattr1_time, cattr127_time, getattr_tm, attr2_tm, attr4_tm, attr128_tm]
    
    from_obj_dict.get_time()
    for obj in all_list:
        obj.get_time()
    
    table = []
    formatters = {
                    'time ns' : lambda x : Formatter.center_dot(x, 1000 * 1000 * 1000),
                    'time/(a.b time)' : lambda x : "{0:.1f}".format(x),
                    "proc ticks" : lambda x : str(int(x)),
                    "diff %" : lambda x : str(int(x * 100))
                  }

    names = ["Operation", "time ns", "diff %", "time/(a.b time)", "proc ticks"]
    allign = ["c", ">", ">", ">", ">"]

    for obj in all_list:
        obj.get_time()
        table.append([obj.msg, obj.tm , obj.diff, obj.tm / from_obj_dict.tm, obj.tm * 2 * 1000 * 1000 * 1000])
    
    sys.stdout.write(Formatter.format_table(
            table, names, formats=formatters, allign=allign) + "\n")


if __name__ == "__main__":
    #main()
    #range_scan("pass", "")
    show_time("c func call", "cadd(1,1)", "import python_imp\nfrom my_mod import add as cadd", num1=1024)
    show_time("int add", "1 + 1", "", num1=1024)



