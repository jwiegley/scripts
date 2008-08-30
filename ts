#!/bin/bash
clear; exec tree -ACF "$@" | less -r -M --quit-if-one-screen
