#!/bin/bash -xe

#HDIR=$HOME/.nix-profile/share/hoogle-4.2.28/databases
HDIR=$HOME/Library/Hoogle

test -d $HDIR || (sudo mkdir -p $HDIR && sudo chown johnw $HDIR)
cd $HDIR

function import_dbs() {
    find -L $1 -name '*.txt' \
        | parallel 'cp -p {} .; chmod 644 {/}; perl -i -pe "print \"\@url file://{//}/index.html\n\" if /^\@version/;" {/}; hoogle convert {/}'
}

rm -f *.txt *.hoo

import_dbs $HOME/.nix-profile/share/doc/

rm -f default.hoo rehoo*

time hoogle data -d $HDIR --redownload -l $(echo *.txt | sed 's/\.txt//g')
time rehoo -j4 -c64 .
