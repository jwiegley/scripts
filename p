#!/bin/sh

if [ -x ~/src/branches/archive/push ]; then
   sh ~/src/branches/archive/push
else
   git push
fi
