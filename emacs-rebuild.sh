#!/bin/bash

set -e

if [[ "$1" == "alt" ]]; then
    STOW_NAME=emacs-release-alt
    APP_INSTALL_DIR=/Applications
    shift 1
else
    STOW_NAME=emacs-release
    APP_INSTALL_DIR=/Applications/Misc
fi

INSTALL_DIR=/usr/local/stow/$STOW_NAME

test -f Makefile && test -f src/Makefile && make distclean

rm -fr $APP_INSTALL_DIR/Emacs.app

(cd /usr/local/stow; sudo stow -D $STOW_NAME)
rm -fr $INSTALL_DIR

./configure --prefix=$INSTALL_DIR \
    --with-mac --enable-mac-app=$APP_INSTALL_DIR \
    CC=/usr/local/bin/clang CFLAGS=-O3 \
    CPPFLAGS=-I/opt/local/include LDFLAGS="-O3 -L/opt/local/lib"

JOBS=-j$(sysctl hw.ncpu | awk '{print $2}')

nice -n 20 make $JOBS "$@"
make install

rm -f $INSTALL_DIR/share/info/dir
(cd /usr/local/stow; sudo stow $STOW_NAME)

exit 0
