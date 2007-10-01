#!/bin/sh
java -jar $HOME/Library/Java/saxon8.jar -snone "$2" "$1" | tidify
