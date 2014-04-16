#!/bin/bash

export PATH=$HOME/bin:$HOME/.cabal/bin:$PATH

installed() {
    ghc-pkg latest $1 > /dev/null 2>&1
}

install() {
    echo cabal install "$@"
    cabal install --haddock-hoogle --haddock-html       \
        --haddock-executables --haddock-internal        \
        --haddock-hyperlink-source "$@"
}

install_prereqs() {
    # if ! installed Cabal; then
    #     install Cabal cabal-install
    # fi

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

    # if ! installed text-icu; then
    #     DYLD_LIBRARY_PATH=/usr/local/opt/icu4c/lib                      \
    #         install -j1 text-icu                                        \
    #             --extra-include-dirs=/usr/local/opt/icu4c/include       \
    #             --extra-lib-dirs=/usr/local/opt/icu4c/lib
    # fi
    # if ! installed libxml-sax; then
    #     PKG_CONFIG_PATH=/usr/local/opt/libxml2/lib/pkgconfig            \
    #         install -j1 libxml-sax                                      \
    #             --extra-include-dirs=/usr/local/opt/libxml2/include     \
    #             --extra-lib-dirs=/usr/local/opt/libxml2/lib
    # fi
    # if ! installed readline; then
    #     DYLD_LIBRARY_PATH=/usr/local/opt/readline/lib                                           \
    #         install -j1 readline                                                                \
    #             --extra-include-dirs=/usr/local/opt/readline/include                            \
    #             --extra-lib-dirs=/usr/local/opt/readline/lib                                    \
    #             --configure-option=--with-readline-includes=/usr/local/opt/readline/include     \
    #             --configure-option=--with-readline-libraries=/usr/local/opt/readline/lib
    # fi
    # if ! installed libffi; then
    #     DYLD_LIBRARY_PATH=/usr/local/opt/libffi/lib                     \
    #     PKG_CONFIG_PATH=/usr/local/opt/libffi/lib/pkgconfig             \
    #         install -j1 libffi                                          \
    #             --extra-include-dirs=/usr/local/opt/libffi/include      \
    #             --extra-lib-dirs=/usr/local/opt/libffi/lib
    # fi
    if ! installed text-icu; then
        install -j1 text-icu                                    \
            --extra-include-dirs=$HOME/.nix-profile/include     \
            --extra-lib-dirs=$HOME/.nix-profile/lib
    fi
    if ! installed libxml-sax; then
        install -j1 libxml-sax                                  \
            --extra-include-dirs=$HOME/.nix-profile/include     \
            --extra-lib-dirs=$HOME/.nix-profile/lib
    fi
    if ! installed readline; then
        install -j1 readline                                                            \
            --extra-include-dirs=$HOME/.nix-profile/include                             \
            --extra-lib-dirs=$HOME/.nix-profile/lib                                     \
            --configure-option=--with-readline-includes=$HOME/.nix-profile/include      \
            --configure-option=--with-readline-libraries=$HOME/.nix-profile/lib
    fi
    if ! installed libffi; then
        install -j1 libffi                                      \
            --extra-include-dirs=$HOME/.nix-profile/include     \
            --extra-lib-dirs=$HOME/.nix-profile/lib
    fi
}

install_postreqs() {
    if ! test -x "$(which gtk2hsTypeGen)"; then
        install -f have-quartz-gtk -j gtk2hs-buildtools
    fi
    if ! installed glib; then
        install -f have-quartz-gtk -j glib gtk cairo
    fi
    if ! test -x "$(which threadscope)"; then
        install -f have-quartz-gtk -j threadscope splot #timeplot
    fi
}

do_cabal() {
    $1 install -j --only-dependencies --force-reinstalls --dry-run      \
        | perl -i -ne 'print unless / /;'                               \
        | perl -i -ne 'print if /-[0-9]+/;'                             \
        | perl -pe 's/-[0-9].+//;'
}

cd ~/src/haskell-deps
cabal install

install_prereqs

uniqify /tmp/deps
install "$@" -j $(< /tmp/deps) || (echo "Cabal build plain failed"; exit 1)

#install_postreqs

ghc-pkg check
