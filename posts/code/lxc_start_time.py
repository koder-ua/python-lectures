#!/bin/env python
# -*- coding:utf8 -*-

import time
import socket
import libvirt

c = libvirt.open("lxc:///")
dom = open("lxc.xml").read()

t = time.time()
c.createXML(dom, 0)
print "Time 1", time.time() - t
try:
	while True:
		try:
			socket.socket().connect(("192.168.122.190", 22))
			dt =  time.time() - t
			print "Time 2", dt
			
			break
		except:
			# на самм деле будет спать больше
			time.sleep(0.001)

finally:
	vm = c.lookupByName('test11')
	vm.destroy()

print "SSH available after", dt, "seconds"
