#!/bin/bash

test last-sync-start -nt last-sync-ready || touch -r last-sync-start last-sync
touch last-sync-start

rsync -av --del --delete-excluded --exclude=obsolete_packs \
    bzr.sv.gnu.org::bzr/emacs/ emacs.bzr/

cd emacs.bzr
find * -path "*/.bzr/branch/last-revision" | while read r; do
  test $r -ot ../last-sync && continue
  b=${r%/.bzr/*}
  b2=$b
  test $b = trunk && b2=master
  test $b = master && b2=bzr/master
  echo $b
  bzr fast-export --plain --marks=../bzr-marks -b $b2 $b | (
    cd ../emacs.git
    git fast-import --quiet --export-marks=../git-marks --import-marks=../git-marks
  )
done
cd ../emacs.git
touch ../last-sync-ready
