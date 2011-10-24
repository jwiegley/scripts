#!/bin/bash

LOGS=$HOME/dl/logs

if [[ ! -d $LOGS ]]; then
    mkdir -p $LOGS
fi

/bin/rm -f $LOGS/*

find "${1:-$PWD}" -name '*.xml' -type f | \
while read file; do
    dir=$(dirname "$file")
    #nick=$(dirname "$dir")
    #nick=$(basename "$nick")
    nick=$(basename "$dir")

    cat "$file" >> $LOGS/"$nick".txt
done

perl -i -ne 'print unless /^<\?xml/;' $LOGS/*
perl -i -ne 'print unless /^<(chat|event)/;' $LOGS/*

perl -i -pe 's/^<message.*time="([-0-9]+?)T([0-9]+:[0-9]+):[^"]+?".*?alias="([^"]+?)">(.+?)<\/message>/\1 \2 | \3: \4/;' $LOGS/*
perl -i -pe 's/^<message sender="([^"]+?)" time="([-0-9]+?)T([0-9]+:[0-9]+):[^"]+?">(.+?)<\/message>/\1 \2 | \3: \4/;' $LOGS/*
perl -i -ne 'print unless /^<\/chat>$/;' $LOGS/*
perl -i -pe 's/<\/?(div|span)[^>]*>//g;' $LOGS/*
perl -i -pe 's/<br ?\/?>/\n/g;' $LOGS/*
perl -i -pe "s/&apos;/'/g;" $LOGS/*
perl -i -pe 's/&amp;/&/g;' $LOGS/*
perl -i -pe 's/&lt;/</g;' $LOGS/*
perl -i -pe 's/&gt;/>/g;' $LOGS/*
perl -i -pe 's/&quot;/"/g;' $LOGS/*
perl -i -ne 'print unless /^<status type.*"\/>$/;' $LOGS/*
perl -i -ne 'print unless /^<status type.*?>.*<\/status>$/;' $LOGS/*
perl -i -pe 's/<a href="([^"]+?)"( style=[^>]+?)?>([^<]+?)<\/a>/[[\1][\2]]/g;' $LOGS/*
perl -i -pe 's/\[\[(.+?)\]\[\1\]\]/[[\1]]/g;' $LOGS/*
perl -i -pe 's/\[\[(.+?)\]\[\]\]/[[\1]]/g;' $LOGS/*
