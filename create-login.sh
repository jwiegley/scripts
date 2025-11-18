#!/usr/bin/env bash

TITLE=$1
LOGIN=$2
PASS=$3

./op get template Login                                                 \
  | jq -r "$(cat << EOF | xargs
        .fields
          |= map( select(.name == \"username\").value = \"$LOGIN\"
                | select(.name == \"password\").value = \"$PASS\"
                )
EOF
)"                                                                      \
  | ./op encode                                                         \
  | xargs ./op create item Login --title="$TITLE" --vault=Personal
