#!/usr/bin/env python
import os

f = os.popen("bc", 'w')
f.write("1+1")
#print(f.readlines())
#for l in f.readlines():
#    print(l)
#print(dir(f))
#l = os.system("ls")
#print("result of os.system('ls')=", l)
#print(os.listdir("."))
#print("hello world")
