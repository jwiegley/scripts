#!/bin/sh

if [ ! -d /media/cdrom ]; then
  mkdir /media/cdrom
fi

mount /dev/cdrom /media/cdrom
sleep 1

cd /tmp
tar xzf /media/cdrom/VMwareTools-*.tar.gz
rm -fr vmware-tools-distrib
cd vmware-tools-distrib
./vmware-install.pl
