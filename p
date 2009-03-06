#!/bin/sh

if [ "$1" = --merge ]; then
    git checkout master
    git merge --no-ff next
fi

if [ -x ./tools/push ]; then
   sh ./tools/push
else
   git push
fi
