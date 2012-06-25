#!/usr/bin/python

import getpass
import sys
import urllib
import urllib2

logname = getpass.getuser() or 'tmp'
form = {}

try:
    f = open('/tmp/oct-%s/server' % logname)
    server = f.read()
    f.close()
except:
    print >> sys.stderr, "Error: no plotting server set."
    sys.exit(1)

for fname in ('data', 'dataset', 'title', 'x-label', 'y-label', 'comment'):
    try:
        f = open('/tmp/oct-%s/%s' % (logname, fname))
        form[fname] = ';'.join(f.read().split('\n'))
        f.close()
    except:
        pass
form = urllib.urlencode(form)

try:
    resp = urllib2.urlopen(urllib2.Request(server, form))
    print resp.read()
except:
    print >> sys.stderr, "Error: couldn't reach plotting server."
    raise
    sys.exit(2)
