#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing... Hit Ctrl-C to end.\n");
}

tcp:::accept-established
{
	@num[args[2]->ip_saddr, args[4]->tcp_dport] = count();
}

dtrace:::END
{
	printf("   %-26s %-8s %8s\n", "HOST", "PORT", "COUNT");
	printa("   %-26s %-8d %@8d\n", @num);
}
