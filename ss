#!/bin/bash
exec ssh -t "$@" exec screen -UDR || ssh -t "$@"
