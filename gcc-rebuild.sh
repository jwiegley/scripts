#!/bin/bash

set -e

SRC=/usr/local/src
STOW=/usr/local/stow
GMP=$STOW/gmp-4.3.2
MPFR=$STOW/mpfr-2.4.2
MPC=$STOW/mpc-0.8.1

if [[ -d /usr/src/redhat/BUILD ]]; then
    PRODUCTS=/usr/src/redhat/BUILD
elif [[ -d $HOME/Products ]]; then
    PRODUCTS=$HOME/Products
else
    PRODUCTS=/tmp
fi

major=4.7
minor=0
gccname=gcc-${major}
gccsuffix=-mp-${major}

export PATH=/usr/bin:/bin
export LD_LIBRARY_PATH=$GMP/lib:$MPFR/lib:$MPC/lib

if [[ -x /usr/bin/otool ]]; then
    export AR_FOR_TARGET=/usr/bin/ar
    export AS_FOR_TARGET=/usr/bin/as
    export LD_FOR_TARGET=/usr/bin/ld
    export NM_FOR_TARGET=/usr/bin/nm
    export OBJDUMP_FOR_TARGET=/usr/bin/objdump
    export RANLIB_FOR_TARGET=/usr/bin/ranlib
    export STRIP_FOR_TARGET=/usr/bin/strip
    export OTOOL=/usr/bin/otool
    export OTOOL64=/usr/bin/otool
    export DYLD_LIBRARY_PATH=$LD_LIBRARY_PATH
fi

########################################################################

if [[ ! -d $GMP ]]; then
    cd $SRC/$(basename $GMP)

    if [[ -d "$PRODUCTS" ]]; then
        if [[ -d "$PRODUCTS/$(basename $GMP)" ]]; then
            rm -fr "$PRODUCTS/$(basename $GMP)"
        fi
        mkdir -p "$PRODUCTS/$(basename $GMP)"
        cd "$PRODUCTS/$(basename $GMP)"
    fi

    test -f Makefile && make distclean
    $SRC/$(basename $GMP)/configure --prefix=$GMP   \
        2>&1 | tee gcc-rebuild.log

    make "$@" 2>&1 | tee gcc-rebuild.log
    make install
fi

########################################################################

if [[ ! -d $MPFR ]]; then
    cd $SRC/$(basename $MPFR)

    if [[ -d "$PRODUCTS" ]]; then
        if [[ -d "$PRODUCTS/$(basename $MPFR)" ]]; then
            rm -fr "$PRODUCTS/$(basename $MPFR)"
        fi
        mkdir -p "$PRODUCTS/$(basename $MPFR)"
        cd "$PRODUCTS/$(basename $MPFR)"
    fi

    test -f Makefile && make distclean
    $SRC/$(basename $MPFR)/configure --prefix=$MPFR \
        --with-gmp=$GMP                             \
        2>&1 | tee gcc-rebuild.log

    make "$@" 2>&1 | tee gcc-rebuild.log
    make install
fi

########################################################################

if [[ ! -d $MPC ]]; then
    cd $SRC/$(basename $MPC)

    if [[ -d "$PRODUCTS" ]]; then
        if [[ -d "$PRODUCTS/$(basename $MPC)" ]]; then
            rm -fr "$PRODUCTS/$(basename $MPC)"
        fi
        mkdir -p "$PRODUCTS/$(basename $MPC)"
        cd "$PRODUCTS/$(basename $MPC)"
    fi

    test -f Makefile && make distclean
    $SRC/$(basename $MPC)/configure --prefix=$MPC   \
        --with-gmp=$GMP --with-mpfr=$MPFR           \
        2>&1 | tee gcc-rebuild.log

    make "$@" 2>&1 | tee gcc-rebuild.log
    make install
fi

########################################################################

cd $STOW
test -d ${gccname} && which stow && stow -D $gccname
test -d ${gccname}.old && rm -fr ${gccname}.old
test -d ${gccname} && mv $gccname ${gccname}.old

cd $SRC/gcc

if [[ -d "$PRODUCTS" ]]; then
    if [[ -d "$PRODUCTS/$gccname" ]]; then
        rm -fr "$PRODUCTS/$gccname"
    fi
    mkdir -p "$PRODUCTS/$gccname"
    cd "$PRODUCTS/$gccname"
fi

test -f Makefile && make distclean
$SRC/gcc/configure --prefix=$STOW/$gccname      \
    --disable-bootstrap                         \
    --disable-multilib                          \
    --disable-nls                               \
    --enable-threads                            \
    --enable-languages=c,c++                    \
    --enable-stage1-checking                    \
    --program-suffix=$gccsuffix                 \
    --with-libiconv-prefix=/usr                 \
    --with-gmp=$GMP                             \
    --with-mpc=$MPC                             \
    --with-mpfr=$MPFR                           \
    --with-system-zlib                          \
    2>&1 | tee gcc-rebuild.log

make "$@" 2>&1 | tee gcc-rebuild.log
make install

cd $STOW
rm -f /usr/local/stow/gcc-4.7/share/info/dir
which stow && stow $gccname

########################################################################

if [[ -d $HOME/src/ledger/lib && -d /Volumes/Boost ]]; then
    cd $HOME/src/ledger/lib
    make GCC_VERSION=$major clean
    make GCC_VERSION=$major OPTJ="$@"

elif [[ -d /usr/local/src/boost_1_48_0 ]]; then
    echo "using gcc : 4.7 : g++-mp-4.7 ;" > $HOME/user-config.jam
    sh bootstrap.sh
    ./b2 "$@" debug --prefix=$STOW/boost_1_48_0-gcc47           \
        --build-dir=$PRODUCTS/boost_1_48_0-gcc47                \
        --layout=versioned link=shared threading=single install
fi

########################################################################

exit 0

# gcc-rebuild.sh ends here
