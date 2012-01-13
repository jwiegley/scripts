#!/usr/sbin/dtrace -s

#pragma D option quiet
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
	printf("%-8s %5s %6s %6s %s\n", "TIME(ms)", "UID", "PID", "PPID",
	    "COMMAND");
	start = timestamp;
}

proc:::exec-success
{
	printf("%-8d %5d %6d %6d %s\n", (timestamp - start) / 1000000,
	    uid, pid, ppid, curpsinfo->pr_psargs);
}
