#!/bin/sh

if [ -x ./archive/push ]; then
   sh ./archive/push
else
   git push
fi
