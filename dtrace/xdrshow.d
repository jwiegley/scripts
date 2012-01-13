#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing XDR calls... Hit Ctrl-C to end.\n");
}

fbt::xdr_*:entry
{
	@num[execname, func(caller), probefunc] = count();
}

dtrace:::END
{
	printf(" %-12s %-28s %-25s %9s\n", "PROCESS", "CALLER", "XDR_FUNCTION",
	    "COUNT");
	printa(" %-12.12s %-28a %-25s %@9d\n", @num);
}
