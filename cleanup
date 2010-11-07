#!/usr/bin/env python

import os
import re
import sys
import getopt
import subprocess
import random
import logging as l

sys.path.append('/Users/johnw/src/dirscan')

from dirscan  import *
from datetime import *
from os.path  import *
from stat     import *

from fcntl import flock, LOCK_SH, LOCK_EX, LOCK_UN

args   = None
debug  = False
status = False
opts   = { 'dryrun': False, 'ages': False }

lockfile = open('/tmp/cleaup.lock', 'wb')
flock(lockfile, LOCK_EX)

if len(sys.argv) > 1:
    options, args = getopt(sys.argv[1:], 'nvuA', {})

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
    DirScanner(directory        = expanduser('~/.Trash'),
               days             = 14,
               cacheAttrs       = True,
               maxSize          = '1%',
               sudo             = True,
               depth            = 0,
               minimalScan      = True,
               onEntryPastLimit = safeRemove,
               **opts).scanEntries()

    if isdir('/.Trashes/501'):
        DirScanner(directory        = '/.Trashes/501',
                   days             = 7,
                   cacheAttrs       = True,
                   maxSize          = '1%',
                   sudo             = True,
                   depth            = 0,
                   minimalScan      = True,
                   onEntryPastLimit = safeRemove,
                   **opts).scanEntries()

    for root in [ "", "RAID" ]:
        if not isdir(join("/Volumes", root)): continue
        for name in os.listdir(join("/Volumes", root)):
            path = join("/Volumes", root, name, ".Trashes", "501")
            if exists(path):
                DirScanner(directory        = path,
                           days             = 14,
                           cacheAttrs       = True,
                           maxSize          = '2%',
                           sudo             = True,
                           depth            = 0,
                           minimalScan      = True,
                           onEntryPastLimit = safeRemove,
                           **opts).scanEntries()

if not args or "backups" in args:
    DirScanner(directory        = expanduser('~/.emacs.d/backups'),
               days             = 28,
               mtime            = True,
               sudo             = True,
               depth            = 0,
               maxSize          = '1%',
               minimalScan      = True,
               onEntryPastLimit = safeRemove,
               **opts).scanEntries()

    for name in os.listdir("/Volumes"):
        path = join("/Volumes", name, ".backups")
        if exists(path):
            DirScanner(directory        = path,
                       days             = 28,
                       mtime            = True,
                       sudo             = True,
                       depth            = 0,
                       maxSize          = '1%',
                       minimalScan      = True,
                       onEntryPastLimit = safeRemove,
                       **opts).scanEntries()

########################################################################

sys.exit(0)

window = 14

random.seed()

def verifyContents(entry):
    if not entry.exists() or entry.isDirectory():
        return False

    checksumSet = False
    if not opts['dryrun']:
        p = subprocess.Popen("xattr -p checksum-sha1 '%s'" % entry.path,
                             shell = True, stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE)
        sts = os.waitpid(p.pid, 0)
        if sts[1] == 0:
            sha = p.stdout.read()[:-1]
            print "ADDED: %s (SHA1 %s)" % (entry.path, sha)
            entry._checksum = sha # we know what it should be from disk
            checksumSet = True

    if not checksumSet:
        print "ADDED: %s (SHA1 %s)" % (entry.path, entry.checksum)

    entry._lastCheck = rightNow - timedelta(random.randint(0, window))

    return True

def alertAdminChanged(entry):
    if not entry.exists() or entry.isDirectory():
        return False
    print "CHANGED:", entry.path
    with open(expanduser('~/Desktop/verify.log'), "a") as fd:
        fd.write("%s - CHANGED: %s\n" % (rightNow, entry.path))
    return True

def alertAdminRemoved(entry):
    if not entry.exists() or entry.isDirectory():
        return False
    print "REMOVED:", entry.path
    return True

for path in [ '/Volumes/RAID/Archives'
            , '/Volumes/RAID/Backups'
            , '/Volumes/RAID/Media'
            ]:
    if isdir(path):
        DirScanner(directory         = expanduser(path),
                   check             = True,
                   checkWindow       = window,
                   ignoreFiles       = [ '^\.files\.dat$'
                                       , '^\.DS_Store$'
                                       , '^\.localized$'
                                       , '^\.git$'
                                       , '\.dtMeta$'
                                       , '^Settings.plist$'
                                       , '\.sparsebundle$'
                                       , '^[0-9]{18}$'
                                       , '^Saves$'
                                       , '^Cache$'
                                       , '^Mobile Applications$'
                                       , '\.dxo$'
                                       , '^\._'

                                       , '^AlbumData2\.xml$'
                                       , '^AlbumData\.xml'
                                       , '^Metadata Backup$'
                                       , '^Thumb64Segment\.data$'
                                       , '^ThumbJPGSegment\.data'
                                       , '^\.ipspot_update$'
                                       , '^face\.db$'
                                       , '^face_blob\.db$'
                                       , '^iPhotoAux\.db'
                                       , '^iPhotoMain\.db'
                                       , '^iPod Photo Cache$'
                                       ],
                   tempDirectory     = '/Volumes/RAID/.Caches',
                   useChecksumAlways = True,
                   onEntryAdded      = verifyContents,
                   onEntryChanged    = alertAdminChanged,
                   onEntryRemoved    = alertAdminRemoved,
                   **opts).scanEntries()

flock(lockfile, LOCK_UN)

# cleanup.py ends here
