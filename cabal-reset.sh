#!/bin/sh -x

set -e

export PATH=$HOME/bin:$HOME/.cabal/bin:$PATH

/bin/rm -fr ~/.ghc/*

for i in lib logs packages setup-exe-cache; do
    /bin/rm -fr ~/.cabal/$i
done

if [[ "$1" == --full ]]; then
    /bin/rm -fr ~/.cabal/share/doc ~/.cabal/share/*-*
fi

# If we have no cabal-dev binary, build it first and wipe out the older build
# products it installs.
if [ ! -x ~/.cabal/bin/cabal-dev ]; then
    cabal install --disable-executable-dynamic cabal-dev --force-reinstalls
    /bin/rm -fr ~/.ghc ~/.cabal/lib/*
fi

exit 0
