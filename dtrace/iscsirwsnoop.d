#!/usr/sbin/dtrace -s

#pragma D option quiet
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
	printf("%-16s %-18s %2s %-8s %6s\n", "TIME(us)", "CLIENT", "OP",
	    "BYTES", "LUN");
}

iscsi*:::data-send
{
	printf("%-16d %-18s %2s %-8d %6d\n", timestamp / 1000,
	    args[0]->ci_remote, "R", args[1]->ii_datalen, args[1]->ii_lun);
}

iscsi*:::data-receive
{
	printf("%-16d %-18s %2s %-8d %6d\n", timestamp / 1000,
	    args[0]->ci_remote, "W", args[1]->ii_datalen, args[1]->ii_lun);
}
