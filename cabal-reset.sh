#!/bin/sh -x

set -e

export PATH=$HOME/bin:$HOME/.cabal/bin:$PATH

/bin/rm -fr ~/.ghc ~/.cabal/lib/*

cabal update

# If we have no cabal-dev binary, build it first and wipe out the older build
# products it installs.
if [ ! -x ~/.cabal/bin/cabal-dev ]; then
    cabal install --disable-executable-dynamic cabal-dev --force-reinstalls
    /bin/rm -fr ~/.ghc ~/.cabal/lib/*
fi

exit 0
