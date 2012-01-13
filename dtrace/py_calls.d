#!/usr/sbin/dtrace -Zs

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing Python... Hit Ctrl-C to end.\n");
}

python*:::function-entry
{
	@funcs[pid, basename(copyinstr(arg0)), copyinstr(arg1)] = count();
}

dtrace:::END
{
	printf("%-6s %-30s %-30s %8s\n", "PID", "FILE", "FUNC", "CALLS");
	printa("%-6d %-30s %-30s %@8d\n", @funcs);
}
