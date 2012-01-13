#!/usr/sbin/dtrace -s

tcp:::receive
{
	@bytes[args[2]->ip_saddr, args[4]->tcp_dport] =
	    quantize(args[2]->ip_plength - args[4]->tcp_offset);
}

tcp:::send
{
	@bytes[args[2]->ip_daddr, args[4]->tcp_sport] =
	    quantize(args[2]->ip_plength - args[4]->tcp_offset);
}
