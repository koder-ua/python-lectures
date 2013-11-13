import python_match

def on_val(x):
	print "In on_val :", repr(x)
	return "it works!"

def printM(obj, val):
	print "In print m", obj, val

class M(object):
	pass

@python_match.update
def test():
	#x = M()
	#x.c = 12
	#x.d = 11

	x = 1

	with python_match.match(x) as res:
		1 >> 2
		2 >> on_val(2)
		int >> on_val(int)
		M(c=V_c, d=V_c) >> on_val("equal")
		M(c=V_c, d=V_d) >> printM(x, V_c)
	
	print res.res
	
test()
