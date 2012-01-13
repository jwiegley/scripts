#!/usr/sbin/dtrace -s

#pragma D option quiet
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
	printf("%-20s %6s %6s %6s  %s\n", "ENDTIME",
	    "UID", "PPID", "PID", "PROCESS");
}

proc:::exec-success
{
	printf("%-20Y %6d %6d %6d  %s\n", walltimestamp,
	    uid, ppid, pid, execname);
}
