#!/bin/bash
exec ssh -t "$@" exec screen -DR
