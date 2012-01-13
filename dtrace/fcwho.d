#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing FC... Hit Ctrl-C to end.\n");
}

fc:::
{
	@events[args[0]->ci_remote, probename] = count();
}

dtrace:::END
{
	printf("   %-26s %14s %8s\n", "REMOTE IP", "FC EVENT", "COUNT");
	printa("   %-26s %14s %@8d\n", @events);
}
