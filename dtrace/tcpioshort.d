#!/usr/sbin/dtrace -s

tcp:::send, tcp:::receive
{
	printf("%15s:%-5d  ->  %15s:%-5d %d bytes",
	    args[2]->ip_saddr, args[4]->tcp_sport,
	    args[2]->ip_daddr, args[4]->tcp_dport,
	    args[2]->ip_plength);
}
