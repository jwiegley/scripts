#!/bin/sh
osacompile -o scrivpost.scpt -- scrivpost.applescript
ditto -rsrc scrivpost.scpt scrivpost
chmod a+x scrivpost
cat -- scrivpost.shosa > scrivpost
rm scrivpost.scpt
