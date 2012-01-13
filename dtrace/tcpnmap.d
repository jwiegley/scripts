#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing for possible nmap scans... Hit Ctrl-C to end.\n");
}

tcp:::accept-refused
{
	@num["TCP_connect()_scan", args[2]->ip_daddr] = count();
}

tcp:::receive
/args[4]->tcp_flags == 0/
{
	@num["TCP_null_scan", args[2]->ip_saddr] = count();
}

tcp:::receive
/args[4]->tcp_flags == (TH_URG|TH_PUSH|TH_FIN)/
{
	@num["TCP_Xmas_scan", args[2]->ip_saddr] = count();
}

dtrace:::END
{
	printf("Possible scan events:\n\n");
	printf("   %-24s %-28s %8s\n", "TYPE", "HOST", "COUNT");
	printa("   %-24s %-28s %@8d\n", @num);
}
