#!/usr/bin/env python

import osxtags
import sys

path = sys.argv[1]
tags = sys.argv[2:]

osxtags.addtags(path, tags)
