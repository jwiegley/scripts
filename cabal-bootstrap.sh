#!/bin/bash -xe

export PATH=$HOME/bin:$HOME/.cabal/bin:$PATH
hash -r

cabal-reset.sh "$@"

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

PKG_CONFIG_PATH=/usr/local/opt/libxml2/lib/pkgconfig            \
    cabal install -j1 libxml-sax                                \
        --extra-include-dirs=/usr/local/opt/libxml2/include     \
        --extra-lib-dirs=/usr/local/opt/libxml2/lib

(cd ~/src/tools/readline-1.0.1.0; \
DYLD_LIBRARY_PATH=/usr/local/opt/readline/lib                   \
    cabal install -j1                                           \
        --extra-include-dirs=/usr/local/opt/readline/include    \
        --extra-lib-dirs=/usr/local/opt/readline/lib            \
        --configure-option=--with-readline-includes=/usr/local/opt/readline/include \
        --configure-option=--with-readline-libraries=/usr/local/opt/readline/lib)

if [[ "$1" == --full ]]; then
    (cd ~/src/tools/hS3; cabal install)
    #(cd ~/src/tools/lambdabot76/lambdabot-utils; cabal install)
    #(cd ~/src/tools/lambdabot76; cabal install)
fi

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
    doctest-prop                                \
    ekg                                         \
    hscolour                                    \
    hspec                                       \
    hspec-expectations                          \
    html                                        \
    lens                                        \
    optparse-applicative                        \
    pretty-show                                 \
    quickcheck                                  \
    rex                                         \
    safe                                        \
    shake                                       \
    shelly                                      \
    simple-reflect                              \
    template-haskell                            \
    test-framework                              \
    test-framework-hunit                        \
    test-framework-quickcheck2                  \
    test-framework-th
do
    echo $i >> /tmp/deps
done

if [[ "$1" == --full ]]; then
    for i in                                    \
        hoogle                                  \
        git-annex                               \
        yesod
    do
        echo $i >> /tmp/deps
    done
fi

uniqify /tmp/deps
perl -i -ne 'print unless /cabal-file-th/;' /tmp/deps

cabal install -j $(< /tmp/deps)

if [[ "$1" == --full ]]; then
    for i in ~/Mirrors/ekmett/*; do
        pkg=$(basename $i)
        cabal install $i || echo "Warning: could not install $i"
    done
fi

ghc-pkg check

if [[ "$1" == --full ]]; then
    rebuild-hoogle
    cabal-bootstrap.sh
fi

exit 0
