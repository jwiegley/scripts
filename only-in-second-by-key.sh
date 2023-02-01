#!/bin/sh
exec awk 'NR==FNR{a[$1]; next} FNR==1 || !($1 in a)' "$1" "$2"
