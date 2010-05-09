#!/bin/zsh

find . -name .svn -type d | while read dir; do
    echo SVN: $dir
    (cd "$dir"/.. ; svn -N status)
done

find . -name .git -type d | while read dir; do
    if [ "$dir" != "./.git" ]; then
	echo Git: $dir
	(cd "$dir"/.. ; git status ; git log --oneline origin/master..) \
	    | egrep -v '(nothing to commit \(working directory clean\)|On branch master)'
    fi
done
