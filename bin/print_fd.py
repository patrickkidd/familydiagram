#!/usr/bin/env python

import sys, os.path, pickle, pprint
from PyQt5 import sip

pp = pprint.PrettyPrinter(indent=4)

fpath = os.path.join(sys.argv[1], "diagram.pickle")
with open(fpath, "rb") as f:
    data = pickle.loads(f.read())

pp.pprint(data)
