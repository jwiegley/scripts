#!/bin/sh

if [ -x ./tools/push ]; then
   sh ./tools/push
else
   git push
fi
