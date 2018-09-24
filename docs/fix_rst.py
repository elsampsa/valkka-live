#!/usr/bin/python3
import glob
import re

filenames=glob.glob("generated/*.rst")

for filename in filenames:
  print(filename)
  
  f=open(filename,"r")
  st=f.read()
  f.close()
  
  f=open(filename,"w")
  for line in st.split("\n"):
    p=re.compile("(\s*).. autosummary")
    m=p.findall(line)
    f.write(line+"\n")
    if (len(m)>0):
      f.write(m[0]+"   "+":toctree:\n")
  
