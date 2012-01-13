#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing iSCSI... Hit Ctrl-C to end.\n");
}

iscsi*:::
{
	@events[args[0]->ci_remote, probename] = count();
}

dtrace:::END
{
	printf("   %-26s %14s %8s\n", "REMOTE IP", "iSCSI EVENT", "COUNT");
	printa("   %-26s %14s %@8d\n", @events);
}
