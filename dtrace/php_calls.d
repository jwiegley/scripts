#!/usr/sbin/dtrace -Zs

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing PHP... Hit Ctrl-C to end.\n");
}

php*:::function-entry
{
	@funcs[basename(copyinstr(arg1)), copyinstr(arg0)] = count();
}

dtrace:::END
{
	printf(" %-32s %-32s %8s\n", "FILE", "FUNC", "CALLS");
	printa(" %-32s %-32s %@8d\n", @funcs);
}
