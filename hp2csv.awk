#!/usr/bin/env gawk -f
BEGIN {
    t = 0
    FS = " "
    print "\"time\",\"symbol\",\"value\""
}
# Skip lines that result from file truncation
/^\0\0/ {}
# We don't are about the following
$1 ~ /^JOB/ {}
$1 ~ /^DATE/ {}
$1 ~ /^SAMPLE_UNIT/ {}
$1 ~ /^VALUE_UNIT/ {}
# End of Sample: reset FS to ' '
$1 ~ /^END_SAMPLE/ {
    FS = " "
}
# start of sample: get sample time
$1 ~ /^BEGIN_SAMPLE/ {
    t = $2
    FS = "\t"
}
# Values
FS == "\t" && !/^BEGIN_SAMPLE/ {
    sub(/-[0-9a-f]+:/, ":", $1)
    print t ",\"" $1 "\"," $2
}
