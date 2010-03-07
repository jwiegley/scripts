#!/bin/bash

ROOT=svn://carbon.corp.smartceg.com/project

#svnsync --non-interactive sync file://$(pwd)/svnrepos &
/usr/bin/svnsync sync file://$(pwd)/svnrepos &

for project in $(svn ls $ROOT)
do
    project=$(echo $project | sed 's/\/$//')

    if [[ ! -d gitrepos/${project}.git ]]; then
	echo --- Cloning $project ---

	if [[ ! -d Working ]]; then
	    mkdir Working
	fi

	(cd Working; \
	    git svn clone "$ROOT/$project" \
	    --trunk=trunk --branches=branches --tags=tags $project) \
	        > Working/${project}.log 2>&1

	mv Working/$project/.git gitrepos/${project}.git && \
	    rm -fr Working/$project
    fi
done

if [[ -d Working ]]; then
    rm -fr Working
fi

git find-fetch "$@" gitrepos Projects

if [[ -d /Volumes/d\$/gitrepos ]]; then
    rsync -aP --inplace --delete gitrepos/ /Volumes/d\$/gitrepos/
fi

wait
