#!/bin/bash -x

export PATH=$HOME/bin:$HOME/.cabal/bin:$PATH

#cabal-reset.sh "$@"

install_prereqs() {
    cabal install Cabal cabal-install
    test -x "$(which cabal-meta)" || cabal install cabal-meta cabal-src

    cabal install -j --disable-executable-dynamic alex
    cabal install -j happy c2hs
    cabal install ghc-heap-view --disable-library-profiling

    DYLD_LIBRARY_PATH=/usr/local/opt/icu4c/lib                      \
        cabal install -j1 text-icu                                  \
            --extra-include-dirs=/usr/local/opt/icu4c/include       \
            --extra-lib-dirs=/usr/local/opt/icu4c/lib

    PKG_CONFIG_PATH=/usr/local/opt/libxml2/lib/pkgconfig            \
        cabal install -j1 libxml-sax                                \
            --extra-include-dirs=/usr/local/opt/libxml2/include     \
            --extra-lib-dirs=/usr/local/opt/libxml2/lib

    DYLD_LIBRARY_PATH=/usr/local/opt/readline/lib                   \
        cabal install -j1 readline                                  \
            --extra-include-dirs=/usr/local/opt/readline/include    \
            --extra-lib-dirs=/usr/local/opt/readline/lib            \
            --configure-option=--with-readline-includes=/usr/local/opt/readline/include \
            --configure-option=--with-readline-libraries=/usr/local/opt/readline/lib
}

do_cabal() {
    $1 install -j --only-dependencies --force-reinstalls --dry-run      \
        | perl -i -ne 'print unless / /;'                               \
        | perl -i -ne 'print if /-[0-9]+/;'                             \
        | perl -pe 's/-[0-9].+//;'
}

rm -f /tmp/deps

find ~/Contracts/ ~/src/ -maxdepth 1 -type d | while read dir ; do
    if [[ -f $dir/sources.txt ]]; then
        (cd $dir ; do_cabal cabal-meta >> /tmp/deps) || echo skip
    elif [[ -f "$(echo $dir/*.cabal)" ]]; then
        (cd $dir; do_cabal cabal >> /tmp/deps) || echo skip
    fi
done

for i in                                        \
    HUnit                                       \
    async                                       \
    cabal-meta                                  \
    cabal-src                                   \
    cereal                                      \
    classy-prelude                              \
    conduit                                     \
    cpphs                                       \
    criterion                                   \
    doctest                                     \
    doctest-prop                                \
    ekg                                         \
    hlint                                       \
    hscolour                                    \
    hsenv                                       \
    hspec                                       \
    hspec-expectations                          \
    html                                        \
    layers                                      \
    lens                                        \
    monad-control                               \
    monad-loops                                 \
    optparse-applicative                        \
    pretty-show                                 \
    quickcheck                                  \
    retry                                       \
    rex                                         \
    safe                                        \
    shake                                       \
    shelly                                      \
    simple-reflect                              \
    stm                                         \
    template-haskell
do
    echo $i >> /tmp/deps
done

if [[ "$1" == --full ]]; then
    for i in                                    \
        git-annex                               \
        yesod
    do
        echo $i >> /tmp/deps
    done
fi

uniqify /tmp/deps
perl -i -ne 'print unless /cabal-file-th/;' /tmp/deps

cabal install "$@" -j $(< /tmp/deps) \
    || (echo "Cabal build plain failed"; exit 1)

exit 0

if [[ "$1" == --full ]]; then
    for i in ~/Mirrors/ekmett/*; do
        pkg=$(basename $i)
        cabal install $i || echo "Warning: could not install $i"
    done
fi

(cd /usr/local/tools/hdevtools; cabal install)

ghc-pkg check

if [[ "$1" == --full ]]; then
    rebuild-hoogle

    cabal-reset.sh
    cabal-bootstrap.sh
fi

exit 0
