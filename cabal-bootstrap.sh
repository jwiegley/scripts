#!/bin/bash -x

set -e

export PATH=$HOME/bin:$HOME/.cabal/bin:$PATH
hash -r

cabal update

cabal install Cabal cabal-install
test -x "$(which cabal-meta)" || cabal install cabal-meta cabal-src

cabal install -j --disable-executable-dynamic alex
cabal install -j happy c2hs
cabal install ghc-heap-view --disable-library-profiling

DYLD_LIBRARY_PATH=/usr/local/opt/icu4c/lib                      \
    cabal install -j1 text-icu                                  \
        --extra-include-dirs=/usr/local/opt/icu4c/include       \
        --extra-lib-dirs=/usr/local/opt/icu4c/lib

DYLD_LIBRARY_PATH=/usr/local/opt/readline/lib                   \
    cabal install -j1 readline                                  \
        --extra-include-dirs=/usr/local/opt/readline/include    \
        --extra-lib-dirs=/usr/local/opt/readline/lib            \
        --configure-option=--with-readline-includes=/usr/local/opt/readline/include \
        --configure-option=--with-readline-libraries=/usr/local/opt/readline/lib

do_cabal() {
    $1 install -j --only-dependencies --force-reinstalls --dry-run
}

rm -f /tmp/deps

find ~/src/ -maxdepth 1 -type d | while read dir ; do
    if [[ -f $dir/sources.txt ]]; then
        (cd $dir ; do_cabal cabal-meta >> /tmp/deps) || echo skip
    elif [[ -f "$(echo $dir/*.cabal)" ]]; then
        (cd $dir; do_cabal cabal >> /tmp/deps) || echo skip
    fi
done

perl -i -ne 'print unless / /;' /tmp/deps
perl -i -ne 'print if /-[0-9]+/;' /tmp/deps

for i in                                        \
    HUnit                                       \
    cabal-meta                                  \
    cabal-src                                   \
    cpphs                                       \
    criterion                                   \
    doctest                                     \
    hscolour                                    \
    hspec                                       \
    html                                        \
    pretty-show                                 \
    simple-reflect                              \
    template-haskell                            \
    test-framework                              \
    test-framework-hunit                        \
    test-framework-quickcheck2                  \
    test-framework-th                           \
                                                \
    optparse-applicative                        \
    fay                                         \
    ekg                                         \
    safe
do
    echo $i >> /tmp/deps
done

uniqify /tmp/deps
cabal install -j $(< /tmp/deps)

ghc-pkg check

exit 0
