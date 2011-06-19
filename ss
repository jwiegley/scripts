#!/bin/bash
exec ssh -t -Y -L 4200:127.0.0.1:4243 "$@" exec screen -UDR
