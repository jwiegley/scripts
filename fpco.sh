#!/bin/bash -xe

cd ~/src/fpco

./dev-scripts/build-all.sh --dev -j             \
    --builddir $HOME/Products/fpco/dist         \
    -s $HOME/Products/fpco/cabal-dev

exit 0
