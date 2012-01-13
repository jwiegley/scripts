#!/usr/sbin/dtrace -Zs

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing Ruby... Hit Ctrl-C to end.\n");
}

ruby*:::function-entry
{
	@funcs[pid, basename(copyinstr(arg2)), copyinstr(arg0),
	    copyinstr(arg1)] = count();
}

dtrace:::END
{
	printf("%-6s %-28.28s %-16s %-16s %8s\n", "PID", "FILE", "CLASS",
	    "METHOD", "CALLS");
	printa("%-6d %-28.28s %-16s %-16s %@8d\n", @funcs);
}
