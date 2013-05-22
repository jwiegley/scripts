#!/bin/bash

export PATH=$HOME/bin:$HOME/.cabal/bin:$PATH

rm -f /tmp/deps

#cabal-reset.sh "$@"

installed() {
    ghc-pkg latest $1 > /dev/null 2>&1
}

install() {
    echo cabal install "$@"
    cabal install "$@"
}

install_prereqs() {
    if ! installed Cabal; then
        install Cabal cabal-install
    fi
    test -x "$(which cabal-meta)" || install cabal-meta cabal-src

    if ! test -x "$(which alex)"; then
        install -j --disable-executable-dynamic alex
    fi
    if ! test -x "$(which happy)"; then
        install -j happy
    fi
    if ! test -x "$(which HsColour)"; then
        install -j hscolour
    fi
    if ! test -x "$(which c2hs)"; then
        install -j c2hs
    fi
    # if ! test -x "$(which ghc-heap-view)"; then
    #     install -j ghc-heap-view --disable-library-profiling
    # fi

    if ! installed text-icu; then
        DYLD_LIBRARY_PATH=/usr/local/opt/icu4c/lib                      \
            install -j1 text-icu                                  \
                --extra-include-dirs=/usr/local/opt/icu4c/include       \
                --extra-lib-dirs=/usr/local/opt/icu4c/lib
    fi

    if ! installed libxml-sax; then
        PKG_CONFIG_PATH=/usr/local/opt/libxml2/lib/pkgconfig            \
            install -j1 libxml-sax                                \
                --extra-include-dirs=/usr/local/opt/libxml2/include     \
                --extra-lib-dirs=/usr/local/opt/libxml2/lib
    fi

    if ! installed readline; then
        DYLD_LIBRARY_PATH=/usr/local/opt/readline/lib                   \
            install -j1 readline                                  \
                --extra-include-dirs=/usr/local/opt/readline/include    \
                --extra-lib-dirs=/usr/local/opt/readline/lib            \
                --configure-option=--with-readline-includes=/usr/local/opt/readline/include \
                --configure-option=--with-readline-libraries=/usr/local/opt/readline/lib
    fi

    if ! test -x "$(which gtk2hsTypeGen)"; then
        install -f have-quartz-gtk -j gtk2hs-buildtools
    fi
    if ! installed glib; then
        install -f have-quartz-gtk -j glib gtk cairo
    fi
    if ! test -x "$(which threadscope)"; then
        install -f have-quartz-gtk -j threadscope splot timeplot
    fi

    if ! installed simple-reflect; then
        install simple-reflect
    fi
}

do_cabal() {
    $1 install -j --only-dependencies --force-reinstalls --dry-run      \
        | perl -i -ne 'print unless / /;'                               \
        | perl -i -ne 'print if /-[0-9]+/;'                             \
        | perl -pe 's/-[0-9].+//;'
}

find ~/Contracts/ ~/Projects/ ~/Mirrors/ -maxdepth 1 -type d \
    | while read dir ; do
    if [[ -f $dir/sources.txt ]]; then
        (cd $dir ; do_cabal cabal-meta >> /tmp/deps 2> /dev/null) || echo skip
    elif [[ -f "$(echo $dir/*.cabal)" ]]; then
        (cd $dir; do_cabal cabal >> /tmp/deps 2> /dev/null) || echo skip
    fi
done

cat >> /tmp/deps <<EOF
HUnit
doctest
doctest-prop
hspec
hspec-expectations
quickcheck

simple-reflect
pretty-show

Boolean
adjunctions
async
bifunctors
categories
classy-prelude
comonad
comonad-transformers
composition
cond
conduit
convertible
distributive
either
free
hashable
keys
lens
lifted-async
lifted-base
monad-control
monad-coroutine
monad-loops
monad-par
monad-par-extras
monad-stm
monoid-extras
numbers
operational
parallel
pointed
profunctor-extras
profunctors
reducers
reflection
resourcet
retry
rex
safe
scotty
semigroupoids
semigroups
snappy
speculation
split
spoon
stm
stm-chans
stm-conduit
stm-stats
system-fileio
system-filepath
tagged
tagged-transformer
these
timers
void

configurator
cpphs
ekg
hlint
hscolour
optparse-applicative
orc
shake
shelly
EOF

if ! test -x "$(which cabal-meta)"; then
    echo cabal-meta >> /tmp/deps
    echo cabal-src >> /tmp/deps
fi

for i in                                        \
    agda                                        \
    c2hsc                                       \
    cab                                         \
    cabal-db                                    \
    cabal-dev                                   \
    darcs                                       \
    ghc-core                                    \
    git-all                                     \
    git-annex                                   \
    hasktags                                    \
    hdevtools                                   \
    hledger                                     \
    hlint                                       \
    hobbes                                      \
    hsenv                                       \
    mueval                                      \
    pandoc                                      \
    pointfree                                   \
    rehoo                                       \
    sizes                                       \
    stylish-haskell                             \
    una                                         \
    unlambda                                    \
    yesod
do
    if ! test -x "$(which $i)"; then
        echo $i >> /tmp/deps
    fi
done

# Libraries that are currently broken
for i in                                        \
    cabal-file-th                               \
    linear
do
    perl -i -ne "print unless /$i/;" /tmp/deps
done

install_prereqs

uniqify /tmp/deps
install "$@" -j $(< /tmp/deps) || (echo "Cabal build plain failed"; exit 1)

ghc-pkg check

if [[ "$1" == --full ]]; then
    rebuild-hoogle

    cabal-reset.sh
    cabal-bootstrap.sh
fi

exit 0
