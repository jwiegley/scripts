#!/usr/sbin/dtrace -s

#pragma D option quiet
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
	printf("%-20s  %-24s %-24s %6s\n", "TIME", "REMOTE", "LOCAL", "LPORT");
}

tcp:::accept-established
{
	printf("%-20Y  %-24s %-24s %6d\n", walltimestamp,
	    args[2]->ip_saddr, args[2]->ip_daddr, args[4]->tcp_dport);
}
