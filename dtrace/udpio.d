#!/usr/sbin/dtrace -s

#pragma D option quiet
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
	printf("%-3s  %15s:%-5s      %15s:%-5s  %6s\n", "CPU",
	    "LADDR", "PORT", "RADDR", "PORT", "IPLEN");
}

udp:::send
{
	printf("%-3d  %15s:%-5d  ->  %15s:%-5d  %6d\n", cpu,
	    args[2]->ip_saddr, args[4]->udp_sport,
	    args[2]->ip_daddr, args[4]->udp_dport, args[2]->ip_plength);
}

udp:::receive
{
	printf("%-3d  %15s:%-5d  <-  %15s:%-5d  %6d\n", cpu,
	    args[2]->ip_daddr, args[4]->udp_dport,
	    args[2]->ip_saddr, args[4]->udp_sport, args[2]->ip_plength);
}
