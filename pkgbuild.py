#!/usr/bin/env python

##############################################################################
#
# pkgbuild.py
# version 1.0, by John Wiegley
#
# TODO: [MED]  Generate service manifests, if just an /etc/init.d script
# TODO: [EASY] Allow naming the service (like 'network/dovecot:imap')
#
# This script turns standardish tarballs directly into Solaris packages.  For
# most packages, simply do this:
#
#   pkgbuild.py foo-1.0.tar.xz
#
# At the moment, I depend on a few things:
#
#   1. The tarball is compressed with 'xz'.
#   2. The tarball is named NAME-VERSION.tar.xz.
#   3. The tarball expands to a directory named NAME-VERSION.
#
# Exceptions can be made by subclassing 'Package'.  There are several examples
# of how to do this toward the end of this file.  Look for "CUSTOM".
#
# Also: If, for any package, an SMF manifest file named NAME.xml exists in the
# same directory as the tarball, it will be imported as a service during the
# package's installation scripts (and also properly removed during uninstall).
#
##############################################################################

import sys
import re
import os
import stat
import shutil
import subprocess

from os.path import *

TMPDIR  = '/tmp'
INSTALL = '/usr/bin/ginstall'
os.environ['PATH'] = '/usr/gnu/bin:' + os.environ['PATH']

make_opts = ('-j4',)

def mkreader(*args, **kwargs):
    print args
    kwargs['stdout'] = subprocess.PIPE
    p = subprocess.Popen(args, **kwargs)
    return p.stdout

def mkwriter(*args, **kwargs):
    print args
    kwargs['stdin'] = subprocess.PIPE
    p = subprocess.Popen(args, **kwargs)
    return p.stdin

def shuttle(reader, writer):
    data = reader.read(8192)
    while data:
        writer.write(data)
        data = reader.read(8192)

def shell(*args, **kwargs):
    print args
    if subprocess.call(args, **kwargs) == 0:
        return True
    else:
        raise Exception("Command failed: " + str(args))

class PrototypeFile(object):
    fd             = None
    preinstall_fd  = None
    postinstall_fd = None
    preremove_fd   = None
    postremove_fd  = None

    def __init__(self):
        self.fd = open('prototype', 'w')

    def __del__(self):
        self.close()

    def write(self, data):
        self.fd.write(data)

    def close(self):
        if self.preinstall_fd:
            self.preinstall_fd.close()
            os.chmod('preinstall', 0755)
        if self.postinstall_fd:
            self.postinstall_fd.close()
            os.chmod('postinstall', 0755)
        if self.preremove_fd:
            self.preremove_fd.close()
            os.chmod('preremove', 0755)
        if self.postremove_fd:
            self.postremove_fd.close()
            os.chmod('postremove', 0755)
        self.fd.close()

    def preinstall(self, line):
        if not self.preinstall_fd:
            self.preinstall_fd = open('preinstall', 'w')
            self.preinstall_fd.write('#!/bin/sh\n')
            self.include('preinstall')
        self.preinstall_fd.write(line)
        self.preinstall_fd.write('\n')

    def postinstall(self, line):
        if not self.postinstall_fd:
            self.postinstall_fd = open('postinstall', 'w')
            self.postinstall_fd.write('#!/bin/sh\n')
            self.include('postinstall')
        self.postinstall_fd.write(line)
        self.postinstall_fd.write('\n')

    def preremove(self, line):
        if not self.preremove_fd:
            self.preremove_fd = open('preremove', 'w')
            self.preremove_fd.write('#!/bin/sh\n')
            self.include('preremove')
        self.preremove_fd.write(line)
        self.preremove_fd.write('\n')

    def postremove(self, line):
        if not self.postremove_fd:
            self.postremove_fd = open('postremove', 'w')
            self.postremove_fd.write('#!/bin/sh\n')
            self.include('postremove')
        self.postremove_fd.write(line)
        self.postremove_fd.write('\n')

    def include(self, name, path=None):
        if path:
            self.fd.write('i %s=%s\n' % (name, path))
        else:
            self.fd.write('i %s\n' % name)

class PkgInfoFile(object):
    package  = None
    name     = None
    version  = None
    category = None

    def __init__(self, package, name, version, category='application'):
        self.package  = package
        self.name     = name
        self.version  = version
        self.category = category

    def close(self):
        with open('pkginfo', 'w') as fd:
            fd.write('''PKG=%s
NAME=%s
VERSION=%s
CATEGORY=%s
''' % (self.package, self.name, self.version, self.category))

class Package(object):
    tarball  = ""
    base     = ""
    name     = ""
    version  = ""
    manifest = None

    def __init__(self, tarball):
        match = re.match('(([^0-9]+?)-([-0-9_.]+))\.tar\.[a-z]+$', tarball)
        if not match:
            raise Exception("Cannot parse tarball name: " + tarball)

        self.tarball = match.group(0)
        self.base    = match.group(1)
        self.name    = match.group(2)
        self.version = match.group(3)

        print "Tarball = %s" % self.tarball
        print "Base    = %s" % self.base
        print "Name    = %s" % self.name
        print "Version = %s" % self.version

        path = join(os.getcwd(), '%s.xml' % self.name)
        if isfile(path):
            self.manifest = path
            
    def maybe_call(self, name, *args, **kwargs):
        try: method = getattr(self, name)
        except AttributeError: pass
        else: method(*args, **kwargs)

    def clean(self):
        if isdir(self.base):
            shutil.rmtree(self.base)

    def unpack(self):
        assert isfile(self.tarball)

        if '.xz' in self.tarball:
            if not isfile('/usr/bin/xz'):
                raise Exception('Please install the xz package')

            shuttle(mkreader("xz", "-dc", self.tarball),
                    mkwriter("tar", "-xf", "-"))

        elif '.bz2' in self.tarball:
            if not isfile('/usr/bin/bzip2'):
                raise Exception('Please install the bzip2 package')

            shuttle(mkreader("bzip2", "-dc", self.tarball),
                    mkwriter("tar", "-xf", "-"))

        elif '.gz' in self.tarball:
            if not isfile('/usr/bin/gzip'):
                raise Exception('Please install the gzip package')

            shuttle(mkreader("gzip", "-dc", self.tarball),
                    mkwriter("tar", "-xf", "-"))

        shell('chown', '-R', 'root:root', self.base)

    def prepare(self):
        shell('git', 'init')

        # Remove all hook files
        for entry in os.listdir('.git/hooks'):
            os.remove(join('.git/hooks', entry))

        shell('git', 'add', '.')
        shell('git', 'commit', '-q', '-m', 'Base')
        shell('git', 'gc', '--quiet')

    def configure(self):
        shell('./configure', '--prefix=/usr', '--sysconfdir=/etc')

    def build(self):
        opts = ['make',] + list(make_opts)
        shell(*opts)

    def ignore_products(self):
        with mkreader('git', 'ls-files', '--other', '--exclude-standard') as fd:
            with open('.gitignore', 'w') as ignore:
                for line in fd:
                    ignore.write('/' + line)

    def install(self, staging):
        shell('make', 'INSTALL=%s' % INSTALL, 'DESTDIR=%s' % staging, 'install')

    def package(self):
        staging = join(TMPDIR, 'pkg-staging')
        
        # Clear out the staging area, since we're going to start populating it

        if isdir(staging):
            shutil.rmtree(staging)
        os.makedirs(staging)

        prototype = PrototypeFile()

        if self.manifest:
            profile_dir = join(staging, 'etc/svc/profile')
            if not isdir(profile_dir):
                os.makedirs(profile_dir)
            shutil.copyfile(self.manifest,
                            join(profile_dir, basename(self.manifest)))

            prototype.postinstall('svccfg import /etc/svc/profile/%s' %
                                  basename(self.manifest))
            prototype.preremove('svcadm disable %s' % self.name)
            prototype.postremove('svccfg delete %s' % self.name)
        
        # Install the software into the staging area.  When the software was
        # configured, make sure that --prefix=/usr (or something reasonable),
        # and set --sysconfdir if necessary (if you want to make sure config
        # files go into /etc).

        self.install(staging)
        
        # For directory names, match owner, group, access flags and dates with
        # whatever the system currently has installed.

        for root, dirs, files in os.walk(staging):
            for entry in map(lambda x: join(root, x)[len(staging)+1:], dirs):
                path = join('/', entry)
                if isdir(path):
                    info = os.stat(path)
                    os.chown(join(staging, entry), info.st_uid, info.st_gid)
                    os.chmod(join(staging, entry), info.st_mode)

        # Create the prototype file, and remove the root directory entry
        # (which should never be removed when doing a pkgrm!).

        for line in mkreader('pkgproto', '%s=/' % staging):
            if not re.match('d none / ', line):
                prototype.write(line)

        prototype.include('pkginfo')
        self.maybe_call('extend_prototype', prototype, staging)
        prototype.close()
        self.maybe_call('edit_prototype', prototype, staging)
        prototype = None
        
        # Create the pkginfo description file.  It's spartan.

        pkginfo = PkgInfoFile(self.name, self.name, self.version)
        pkginfo.close()
        
        # Make the package, then move it to the current directory with a
        # versioned pathname.

        self.mkpkg()

    def mkpkg(self):
        shell('pkgmk', '-o')
        shell('pkgtrans', '-s', '/var/spool/pkg',
              join(TMPDIR, '%s.pkg' % self.base), self.name)

    def main(self):
        self.clean()
        self.unpack()
        
        os.chdir(self.base)

        if isfile('/usr/bin/git'):
            self.prepare()

        self.configure()
        self.build()

        if isfile('/usr/bin/git'):
            self.ignore_products()

        self.package()

        path = join(TMPDIR, '%s.pkg' % self.base)
        if isfile(path):
            print '=' * 78
            print 'Package %s built successfully.' % path
            print '=' * 78
        else:
            print '=' * 78
            print '%s FAILED to package!' % self.base
            print '=' * 78

##############################################################################
## CUSTOM PACKAGES ###########################################################
##############################################################################

class Apcupsd(Package):
    def __init__(self, tarball):
        Package.__init__(self, tarball)

    def configure(self):
        shell('./configure', '--prefix=/usr', '--sysconfdir=/etc',
              '--enable-usb')

    def edit_prototype(self, prototype, staging):
        shutil.rmtree(join(staging, 'etc/rc0.d'))
        shutil.rmtree(join(staging, 'etc/rc1.d'))
        shutil.rmtree(join(staging, 'etc/rc2.d'))

        with open('prototype_tmp', 'w') as tmp:
            for line in open('prototype', 'r'):
                if not re.search('/etc/rc', line):
                    tmp.write(line)
        os.remove('prototype')
        os.rename('prototype_tmp', 'prototype')

##############################################################################

class BerkeleyDB(Package):
    def __init__(self, tarball):
        Package.__init__(self, tarball)

    def configure(self):
        os.chdir('build_unix')
        shell('../dist/configure', '--prefix=/usr', '--sysconfdir=/etc')

##############################################################################

class GooglePerftools(Package):
    def __init__(self):
        self.base    = 'google-perftools-1.7'
        self.name    = 'google-perftools'
        self.version = '1.7'

        print "Base    = %s" % self.base
        print "Name    = %s" % self.name
        print "Version = %s" % self.version

    def clean(self): pass
    def unpack(self): pass
    def prepare(self): pass
    def ignore_products(self): pass


class RubyEnterprise(Package):
    def __init__(self, tarball):
        Package.__init__(self, tarball)

    def configure(self):
        os.chdir('source')

        path = os.getcwd()
        try:
            os.chdir('distro')
            perf = GooglePerftools()
            perf.main()
        finally:
            os.chdir(path)

        shell('./configure', '--prefix=/usr', '--sysconfdir=/etc',
              '--enable-mbari-api', 'CFLAGS=-O3')

        with open('Makefile_tmp', 'w') as tmp:
            for line in open('Makefile', 'r'):
                match = re.match('LIBS = (.*)', line)
                if match:
                    tmp.write('LIBS = $(PRELIBS) ' + match.group(1) + '\n')
                else:
                    tmp.write(line)
        os.remove('Makefile')
        os.rename('Makefile_tmp', 'Makefile')

        with mkwriter('patch', '-p2') as patch:
            patch.write('''
--- a/source/signal.c
+++ b/source/signal.c
@@ -16,6 +16,7 @@
 #include "rubysig.h"
 #include "node.h"
 #include <signal.h>
+#include <ucontext.h>
 #include <stdio.h>
 
 #ifdef __BEOS__
@@ -673,7 +674,7 @@ dump_machine_state(uc)
	     uc->uc_mcontext->__ss.__eip, uc->uc_mcontext->__ss.__cs,
	     uc->uc_mcontext->__ss.__ds, uc->uc_mcontext->__ss.__es,
	     uc->uc_mcontext->__ss.__fs, uc->uc_mcontext->__ss.__gs);
-#elif defined(__i386__)
+#elif 0 && defined(__i386__)
   sig_printf(dump32, uc->uc_mcontext.gregs[REG_EAX], uc->uc_mcontext.gregs[REG_EBX],
	     uc->uc_mcontext.gregs[REG_ECX], uc->uc_mcontext.gregs[REG_EDX],
	     uc->uc_mcontext.gregs[REG_EDI], uc->uc_mcontext.gregs[REG_ESI],
''')

    def build(self):
        shell('make', 'PRELIBS=-Wl,-rpath,/usr/lib -L/usr/lib -ltcmalloc_minimal')

##############################################################################

class Dovecot(Package):
    def __init__(self, tarball):
        Package.__init__(self, tarball)

    def configure(self):
        shell('./configure', '--prefix=/usr', '--sysconfdir=/etc',
              '--localstatedir=/var')

    def build(self):
        opts = ['make',] + list(make_opts) + \
            [ 'prefix=/usr',
              'sysconfdir=/etc',
              'localstatedir=/var',
              'rundir=/var/run/dovecot',
              'statedir=/var/lib/dovecot' ]
        shell(*opts)

    def install(self, staging):
        opts = ['make',] + \
            [ 'INSTALL=%s' % INSTALL,
              'DESTDIR=%s' % staging,
              'prefix=/usr',
              'sysconfdir=/etc',
              'localstatedir=/var',
              'rundir=/var/run/dovecot',
              'statedir=/var/lib/dovecot',
              'install' ]
        shell(*opts)

    def extend_prototype(self, prototype, staging):
        prototype.postinstall('''
/usr/sbin/useradd -d /usr/lib/dovecot -s /usr/bin/false dovecot
/usr/sbin/useradd -d /usr/lib/dovecot -s /usr/bin/false dovenull

if ! grep -q ^imap /etc/pam.conf; then
    cat <<EOF >> /etc/pam.conf
imap    auth    requisite       pam_authtok_get.so.1
imap    auth    required        pam_unix_auth.so.1
imap    account requisite       pam_roles.so.1
imap    account required        pam_unix_account.so.1
imap    session required        pam_unix_session.so.1
pop3    auth    requisite       pam_authtok_get.so.1
pop3    auth    required        pam_unix_auth.so.1
pop3    account requisite       pam_roles.so.1
pop3    account required        pam_unix_account.so.1
pop3    session required        pam_unix_session.so.1
EOF
fi
/usr/bin/perl
''')
        prototype.postremove('''
/usr/sbin/userdel dovecot
/usr/sbin/userdel dovenull

/usr/bin/perl -i -ne 'print unless /^(imap|pop3)/;' /etc/pam.conf
''')

##############################################################################
##############################################################################
##############################################################################

if __name__ == "__main__":
    for path in sys.argv[1:]:
        if re.match('dovecot-', path):
            Dovecot(path).main()
        elif re.match('apcupsd-', path):
            Apcupsd(path).main()
        elif re.match('ruby-', path):
            RubyEnterprise(path).main()
        elif re.match('db-', path):
            BerkeleyDB(path).main()
        else:
            Package(path).main()

sys.exit(0)

### pkgbuild.py ends here
