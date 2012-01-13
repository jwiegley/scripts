#!/usr/sbin/dtrace -Zs

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing Perl... Hit Ctrl-C to end.\n");
}

perl*:::sub-entry
{
	@subs[pid, basename(copyinstr(arg1)), copyinstr(arg0)] = count();
}

dtrace:::END
{
	printf("%-6s %-30s %-30s %8s\n", "PID", "FILE", "SUB", "CALLS");
	printa("%-6d %-30s %-30s %@8d\n", @subs);
}
