#!/usr/sbin/dtrace -s

#pragma D option quiet
#pragma D option defaultargs
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
	printf("%-12s %6s %6s %-12.12s %-12s %-6s %s\n", "TIME(ms)", "UID",
	    "PID", "PROCESS", "CALL", "BYTES", "PATH");
}

fsinfo:::
/execname != "dtrace" && ($$1 == NULL || $$1 == execname)/
{
	printf("%-12d %6d %6d %-12.12s %-12s %-6d %s\n", timestamp / 1000000,
	    uid, pid, execname, probename, arg1, args[0]->fi_pathname);
}
