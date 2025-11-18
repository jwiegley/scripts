#!/usr/bin/env bash
exec ssh -t "$@" exec screen -UDR || ssh -t "$@"
