#!/bin/bash

patch -p0 < $1/patch-mac
cp -pR $1/mac .
rsync -av $1/src/ src/
cp -pR $1/lisp/term/mac-win.el lisp/term
