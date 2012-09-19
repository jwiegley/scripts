#!/bin/sh

du -shx * .[a-zA-Z0-9_]* | sort -h
