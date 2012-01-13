#!/usr/sbin/dtrace -Zs

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing... Hit Ctrl-C to end.\n");
}

sh*:::function-entry
{
	@calls[basename(copyinstr(arg0)), "func", copyinstr(arg1)] = count();
}

sh*:::builtin-entry
{
	@calls[basename(copyinstr(arg0)), "builtin", copyinstr(arg1)] = count();
}

sh*:::command-entry
{
	@calls[basename(copyinstr(arg0)), "cmd", copyinstr(arg1)] = count();
}

sh*:::subshell-entry
/arg1 != 0/
{
	@calls[basename(copyinstr(arg0)), "subsh", "-"] = count();
}

dtrace:::END
{
	printf(" %-22s %-10s %-32s %8s\n", "FILE", "TYPE", "NAME", "COUNT");
	printa(" %-22s %-10s %-32s %@8d\n", @calls);
}
