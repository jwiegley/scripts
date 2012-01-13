#!/usr/sbin/dtrace -Zs

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing Tcl... Hit Ctrl-C to end.\n");
}

tcl*:::proc-entry
{
	@calls[pid, "proc", copyinstr(arg0)] = count();
}

tcl*:::cmd-entry
{
	@calls[pid, "cmd", copyinstr(arg0)] = count();
}

dtrace:::END
{
	printf(" %6s %-8s %-52s %8s\n", "PID", "TYPE", "NAME", "COUNT");
	printa(" %6d %-8s %-52s %@8d\n", @calls);
}
