#!/bin/sh
osacompile -o blogpost.scpt -- blogpost.applescript
ditto -rsrc blogpost.scpt blogpost
chmod a+x blogpost
cat -- blogpost.shosa > blogpost
rm blogpost.scpt
