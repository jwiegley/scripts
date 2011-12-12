#!/bin/bash -x

set -e

if [[ ! -d gcc ]]; then
    echo There is no gcc directory beneath the current directory
    exit 1
fi

SRC=$(pwd)
ROOT=$(dirname "$SRC")
GMP=gmp-4.3.2
MPFR=mpfr-2.4.2
MPC=mpc-0.8.1
major=4.7
minor=0
nodots=$(echo $major | sed 's/\.//')
gccname=gcc-${major}
gccsuffix=-mp-${major}
boostmajor=1_48
boost=${boostmajor}_0
boostname=boost_$boost-gcc$nodots
boostregex=libboost_regex-xgcc${nodots}-d-${boostmajor}.a

if [[ "$1" == --prefix ]]; then
    shift 1
    if [[ "$1" == stow ]]; then
        usestow=true
        DEST="$ROOT/stow"
        BIN="$ROOT/bin"
        GMPDEST="$DEST/$GMP"
        MPFRDEST="$DEST/$MPFR"
        MPCDEST="$DEST/$MPC"
        GCCDEST="$DEST/$gccname"
        BOOSTDEST="$DEST/$boostname"
    else
        usestow=false
        DEST="$1"
        BIN="$1/bin"
        GMPDEST="$DEST"
        MPFRDEST="$DEST"
        MPCDEST="$DEST"
        GCCDEST="$DEST"
        BOOSTDEST="$DEST"
    fi
    shift 1
else
    usestow=false
    DEST="$ROOT/cpp11"
    BIN="$ROOT/cpp11/bin"
    GMPDEST="$DEST"
    MPFRDEST="$DEST"
    MPCDEST="$DEST"
    GCCDEST="$DEST"
    BOOSTDEST="$DEST"

    test -d "$DEST" || mkdir "$DEST"
fi

if [[ -d /usr/src/redhat/BUILD ]]; then
    PRODUCTS=/usr/src/redhat/BUILD
elif [[ -d $HOME/Products ]]; then
    PRODUCTS=$HOME/Products
else
    PRODUCTS=/tmp
fi

export PATH=/usr/bin:/bin:"$BIN"
export LD_LIBRARY_PATH="$GMPDEST/lib:$MPFRDEST/lib:$MPCDEST/lib"

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
    export OPTIONS=""
    export GCCOPTIONS="--with-libiconv-prefix=/usr --with-system-zlib"
else
    export OPTIONS="--enable-static --disable-shared"
    export GCCOPTIONS=""
fi

function cd_builddir()
{
    if [[ -d "$PRODUCTS" ]]; then
        if [[ -d "$PRODUCTS/$1" ]]; then
            rm -fr "$PRODUCTS/$1"
        fi
        mkdir -p "$PRODUCTS/$1"
        cd "$PRODUCTS/$1"
    fi
}

########################################################################

if [[ ! -f $GMPDEST/lib/libgmp.a ]]; then
    cd $SRC/$GMP
    cd_builddir $GMP

    test -f Makefile && make distclean
    $SRC/$GMP/configure --prefix=$GMPDEST $OPTIONS      \
        2>&1 | tee build.log

    make "$@" 2>&1 | tee build.log
    make install

    if [[ $usestow == true ]]; then
        cd $STOW
        which stow && stow $GMP
    fi
fi

########################################################################

if [[ ! -f $MPFRDEST/lib/libmpfr.a ]]; then
    cd $SRC/$MPFR
    cd_builddir $MPFR

    test -f Makefile && make distclean
    $SRC/$MPFR/configure --prefix=$MPFRDEST $OPTIONS    \
        --with-gmp=$GMPDEST                             \
        2>&1 | tee build.log

    make "$@" 2>&1 | tee build.log
    make install

    if [[ $usestow == true ]]; then
        cd $STOW
        which stow && stow $MPFR
    fi
fi

########################################################################

if [[ ! -f $MPCDEST/lib/libmpc.a ]]; then
    cd $SRC/$MPC
    cd_builddir $MPC

    test -f Makefile && make distclean
    $SRC/$MPC/configure --prefix=$MPCDEST $OPTIONS      \
        --with-gmp=$GMPDEST --with-mpfr=$MPFRDEST       \
        2>&1 | tee build.log

    make "$@" 2>&1 | tee build.log
    make install

    if [[ $usestow == true ]]; then
        cd $STOW
        which stow && stow $MPC
    fi
fi

########################################################################

if [[ ! -x $GCCDEST/bin/g++$gccsuffix ]]; then
    if [[ $usestow == true ]]; then
        cd $STOW
        test -d ${gccname} && which stow && stow -D $gccname
        test -d ${gccname}.old && rm -fr ${gccname}.old
        test -d ${gccname} && mv $gccname ${gccname}.old
    fi

    cd $SRC/gcc
    cd_builddir $gccname

    test -f Makefile && make distclean
    $SRC/gcc/configure --prefix=$GCCDEST $GCCOPTIONS \
        --disable-bootstrap                         \
        --disable-multilib                          \
        --disable-nls                               \
        --enable-threads                            \
        --enable-languages=c,c++                    \
        --program-suffix=$gccsuffix                 \
        --with-gmp=$GMPDEST                         \
        --with-mpc=$MPCDEST                         \
        --with-mpfr=$MPFRDEST                       \
        2>&1 | tee build.log

    make "$@" 2>&1 | tee build.log
    make install

    if [[ $usestow == true ]]; then
        cd $STOW
        rm -f $gccname/share/info/dir
        which stow && stow $gccname
    fi
fi

########################################################################

if [[ ! -f $BOOSTDEST/lib/$boostregex ]]; then
    if [[ -d $SRC/boost_$boost ]]; then
        echo "using gcc : $major : g++$gccsuffix ;" > $HOME/user-config.jam

        cd $SRC/boost_$boost
        if [[ -x /usr/bin/otool ]]; then
            perl -i -pe "s/local command = \\[ common\\.get-invocation-command darwin : g\\+\\+ : .*/local command = [ common.get-invocation-command darwin : g++ : g++$gccsuffix ] ;/;" tools/build/v2/tools/darwin.jam
            perl -i -pe 's/flags darwin\.compile OPTIONS : -no-cpp-precomp -gdwarf-2 (-fexceptions )?;/flags darwin\.compile OPTIONS : -gdwarf-2 \1;/;' tools/build/v2/tools/darwin.jam
        fi

        cd_builddir $boostname
        builddir=$(pwd)

        cd $SRC/boost_$boost
        sh bootstrap.sh
        #./b2 "$@" --prefix=$BOOSTDEST --build-dir=$builddir --layout=versioned      \
        #    --build-type=complete link=static define=_GLIBCXX__PTHREADS=1 install
        ./b2 "$@" --prefix=$BOOSTDEST --build-dir=$builddir --layout=versioned      \
            link=shared threading=single define=_GLIBCXX__PTHREADS=1 debug install

        #cd status
        #../b2 define=_GLIBCXX__PTHREADS=1

        rm -f $HOME/user-config.jam

    elif [[ -d $HOME/src/ledger/lib && -d /Volumes/Boost ]]; then
        cd $HOME/src/ledger/lib

        make GCC_VERSION=$major clean
        make GCC_VERSION=$major OPTJ="$@"

    fi
fi

########################################################################

exit 0

# gcc-rebuild.sh ends here
