#!/bin/bash

CNTX=orgs
NAME=kadena-io

for PAGE in 1 2 ; do
    curl -s "https://api.github.com/$CNTX/$NAME/repos?page=$PAGE&per_page=100"  \
        | grep -e 'clone_url*'                                                  \
        | cut -d \" -f 4                                                        \
        | xargs -L1 git clone
done
