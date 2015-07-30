# -*- coding: utf-8 -*-
r""" Import integral lattices data.  

Note: This code can be run on all files in any order. Even if you 
rerun this code on previously entered files, it should have no affect.  
This code checks if the entry exists, if so returns that and updates 
with new information. If the entry does not exist then it creates it 
and returns that.

"""

import sys, time
import re
import json
import sage.all
from sage.all import os

from pymongo.connection import Connection
lat = Connection(port=37010).Lattices.lat

saving = True 

def sd(f):
  for k in f.keys():
    print '%s ---> %s'%(k, f[k])

def makels(li):
  li2 = [str(x) for x in li]
  return ','.join(li2)

def string2list(s):
  s = str(s)
  if s=='': return []
  return [int(a) for a in s.split(',')]

def base_label(dimension,determinant,level,class_number):
    return ".".join([str(dimension),str(determinant),str(level),str(class_number),str(n)])

def last_label(base_label, n):
    return ".".join([str(dimension),str(determinant),str(level),str(class_number),str(n)])

## Main importing function

def do_import(ll):
    level,weight,character,dim,dimtheta,thetas,newpart  = ll
    mykeys = ['', '', '', '', '', '', '']
    data = {}
    for j in range(len(mykeys)):
        data[mykeys[j]] = ll[j]
	
    label = base_label(data['dimension'],data['determinant'],data['level'], data['class_number'])
    data['label'] = label
    form = forms.find_one({'label': label})

    if form is None:
        print "new form"
        form = data
    else:
        print "form already in database"
        form.update(data)
    if saving:
        forms.save(form)

# Loop over files

for path in sys.argv[1:]:
    print path
    filename = os.path.basename(path)
    fn = gzip.open(path) if filename[-3:] == '.gz' else open(path)
    for line in fn.readlines():
        line.strip()
        if re.match(r'\S',line):
            l = json.loads(line)
            do_import(l)
