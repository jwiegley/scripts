#!/bin/bash

switch="-c"
limit=""
#limit="-t (/Liabilities/?(/Huquq/?a/P(2.22AU,m)<=-1.0:a<0):U(a)>99)&a"

if [ "$1" = "-f" ]; then
  switch=""
  shift
fi

if [ "$1" = "-C" -o "$1" = "-U" ]; then
  switch="$1"
  shift
fi

if [ "$1" = "-b" -o "$1" = "-e" ]; then
  switch="$1 $2"
  shift 2
fi

accts="$@"
if [ -z "$accts" ]; then
  accts="-Equity -Income -Expenses"
  accts="$accts -^Retirement"
elif [ "$accts" = "retire" ]; then
  switch="$switch -Q"
  limit=""
else
  limit=""
fi

LEDGER=ledger

if [[ -x ~/Products/ledger/ledger ]]; then
    LEDGER=~/Products/ledger/ledger
fi

#$LEDGER -V $switch $limit -s -S "-U(T)" balance $accts
$LEDGER $switch $limit -s -S "-U(T)" balance $accts
