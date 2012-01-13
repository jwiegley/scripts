#!/usr/sbin/dtrace -s

#pragma D option quiet
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
	printf("%-16s %-18s %2s %-8s %6s\n", "TIME(us)", "CLIENT", "OP",
	    "BYTES", "LUN");
}

iscsi:::xfer-start
{
	printf("%-16d %-18s %2s %-8d %6d\n", timestamp / 1000,
	    args[0]->ci_remote, arg8 ? "R" : "W", args[2]->xfer_len,
	    args[1]->ii_lun);
}
