#!/usr/bin/env python

import sys
import re
import os
import codecs

log     = sys.argv[1]
account = sys.argv[2]
service = sys.argv[3]

dir = os.path.dirname(log)
match = re.match('(\S+) (on )?\(?([0-9]+)[-|]([0-9]+)[-|]([0-9]+)\)?\.AdiumHTMLLog', os.path.basename(log))
if not match:
    sys.stderr.write("File name does not match: %s\n" % log)
    sys.exit(1)

recip = match.group(1)
year  = match.group(3)
month = match.group(4)
day   = match.group(5)

not_first = False
out = None

for line in open(log, 'r'):
    match  = re.search('<div class="(send|receive)"><span class="timestamp">([0-9]+):([0-9]+):([0-9]+)( [AP]M)?</span> <span class="sender">([^:]+): </span><pre class="message">(.+?)</pre></div>$', line)
    if not match:
        continue

    sender = match.group(6)
    msg    = match.group(7)

    hour = int(match.group(2))
    if match.group(5):
        if match.group(5) == " AM" and hour == 12:
            hour = 0
        elif match.group(5) == " PM" and hour != 12:
            hour += 12

    stamp = '%s-%s-%sT%02d:%s:%s-08:00' % (year, month, day, hour, match.group(3), match.group(4))

    if not not_first:
        outname = os.path.join(dir, '%s (%s).chatlog' % (recip, stamp))
        if os.path.exists(outname):
            sys.stderr.write("File already exists: %s\n" % outname)
            sys.exit(1)
        out = open(outname, 'w')
        out.write(u'<?xml version="1.0" encoding="UTF-8" ?>\n')
        out.write(u'<chat xmlns="http://purl.org/net/ulf/ns/0.4-02" account="%s" service="%s"><event type="windowOpened" sender="%s" time="%s"/>\n' % (account, service, account, stamp))
        not_first = stamp

    out.write('<message sender="%s" time="%s"><div><span style="font-family: Lucida Grande; font-size: 12pt;">%s</span></div></message>\n' % (sender, stamp, msg))

if out:
    out.write(u'<event type="windowClosed" sender="%s" time="%s"/>\n' % (account, stamp))
    out.write(u'</chat>\n')

    os.remove(log)
