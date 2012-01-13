#!/usr/sbin/dtrace -Zs

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing Tcl... Hit Ctrl-C to end.\n");
}

tcl*:::cmd-entry
{
	@calls[pid, uid, curpsinfo->pr_psargs] = count();
}

dtrace:::END
{
	printf("   %6s %6s %6s %-55s\n", "PID", "UID", "CMDS", "ARGS");
	printa("   %6d %6d %@6d %-55.55s\n", @calls);
}
