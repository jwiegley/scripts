#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing... Hit Ctrl-C to end.\n");
}

proc:::signal-send
{
	@Count[execname, stringof(args[1]->pr_fname), args[2]] = count();
}

dtrace:::END
{
	printf("%16s %16s %6s %6s\n", "SENDER", "RECIPIENT", "SIG", "COUNT");
	printa("%16s %16s %6d %6@d\n", @Count);
}
