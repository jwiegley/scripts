#!/bin/bash
if test -f $HOME/.gpg-agent-info && \
  kill -0 `cut -d: -f 2 $HOME/.gpg-agent-info` 2>/dev/null; then
    GPG_AGENT_INFO=`cat $HOME/.gpg-agent-info`
    export GPG_AGENT_INFO
else
  eval `$HOME/.nix-profile/bin/gpg-agent --daemon --write-env-file`
fi
export GPG_TTY=`tty`
