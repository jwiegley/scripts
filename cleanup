#!/usr/bin/env python

import os
import re
import sys
import getopt
import logging as l

sys.path.append('/Users/johnw/src/dirscan')

osxtags = None
try:
    import osxtags
except: pass

from dirscan import DirScanner, Entry, safeRun, safeRemove, safeTrash
from datetime import *
from os.path import *
from stat import *

args   = None
debug  = False
status = False

opts   = { 'dryrun': False, 'ages': False }

if len(sys.argv) > 1:
    options, args = getopt.getopt(sys.argv[1:], 'nvuA', {})

    for o, a in options:
        if o in ('-v'):
            debug = True
            l.basicConfig(level = l.DEBUG,
                          format = '[%(levelname)s] %(message)s')
        elif o in ('-u'):
            status = True
            l.basicConfig(level = l.INFO, format = '%(message)s')
        elif o in ('-n'):
            opts['dryrun'] = True
        elif o in ('-A'):
            opts['ages'] = True


if not args or "trash" in args:
    for name in os.listdir("/Volumes"):
        path = join("/Volumes", name, ".Trashes", "501")
        if exists(path):
            DirScanner(directory        = path,
                       days             = 7,
                       cacheAttrs       = True,
                       maxSize          = 1 * 1024 * 1024 * 1024,
                       sudo             = True,
                       depth            = 0,
                       minimalScan      = True,
                       onEntryPastLimit = safeRemove,
                       **opts).scanEntries()

        path = join("/Volumes", name)
        if isdir(path):
            for fs in os.listdir(path):
                fspath = join(path, fs, ".Trashes", "501")
                if exists(fspath):
                    DirScanner(directory        = fspath,
                               days             = 7,
                               cacheAttrs       = True,
                               maxSize          = 2 * 1024 * 1024 * 1024,
                               sudo             = True,
                               depth            = 0,
                               minimalScan      = True,
                               onEntryPastLimit = safeRemove,
                               **opts).scanEntries()

    if isdir('/.Trashes/501'):
        DirScanner(directory        = '/.Trashes/501',
                   days             = 7,
                   cacheAttrs       = True,
                   maxSize          = 2 * 1024 * 1024 * 1024,
                   sudo             = True,
                   depth            = 0,
                   minimalScan      = True,
                   onEntryPastLimit = safeRemove,
                   **opts).scanEntries()

    DirScanner(directory        = expanduser('~/.Trash'),
               days             = 14,
               cacheAttrs       = True,
               maxSize          = 3 * 1024 * 1024 * 1024,
               sudo             = True,
               depth            = 0,
               minimalScan      = True,
               onEntryPastLimit = safeRemove,
               **opts).scanEntries()

    DirScanner(directory        = expanduser('~/Products'),
               days             = 28,
               sudo             = True,
               depth            = 0,
               minimalScan      = True,
               onEntryPastLimit = safeRemove,
               **opts).scanEntries()

if not args or "emacs" in args:
    DirScanner(directory        = expanduser('~/.emacs.d/backups'),
               days             = 28,
               mtime            = True,
               depth            = 0,
               minimalScan      = True,
               onEntryPastLimit = safeRemove,
               **opts).scanEntries()

if isdir("/Volumes/CEG/.backups"):
    DirScanner(directory        = "/Volumes/CEG/.backups",
               days             = 7,
               mtime            = True,
               depth            = 0,
               minimalScan      = True,
               onEntryPastLimit = safeRemove,
               **opts).scanEntries()

# Move new items in Drop Box to the Desktop

#for name in os.listdir(expanduser("~/Public/Drop Box")):
#    if not exists(join(expanduser("~/Desktop"), name)):
#        os.rename(join(expanduser("~/Public/Drop Box"), name),
#                  join(expanduser("~/Desktop"), name))

# Cleanup the Downloads folder

def handleDownload(entry):
    path = entry.path

    if re.search('\.imported$', path):
        safeTrash(entry)

    elif re.search('\.dmg$', path):
        target = join(expanduser("~/Archives/Mac OS X/Software"), basename(path))
        if exists(target):
            os.unlink(target)
        os.rename(path, target)
        os.system("archive \"%s\"" % target)

if args and "downloads" in args:
    DirScanner(directory        = expanduser('~/Downloads'),
               days             = 0.25, # 8 hours
               depth            = 0,
               minimalScan      = True,
               onEntryPastLimit = handleDownload,
               **opts).scanEntries()

