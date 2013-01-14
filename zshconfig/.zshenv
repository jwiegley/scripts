export WORDCHARS=''
export COLUMNS=100
export LEDGER_COLOR=true

setopt SHORT_LOOPS
setopt EXTENDED_GLOB
setopt RE_MATCH_PCRE
setopt NULL_GLOB
setopt NUMERIC_GLOB_SORT

if [ -x $HOME/bin/shell-args ]; then
    eval `$HOME/bin/shell-args`
fi

launchctl limit maxproc 512
