#!/bin/bash
exec ssh -t "$1" exec screen -DR
