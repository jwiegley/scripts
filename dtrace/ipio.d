#!/usr/sbin/dtrace -s

#pragma D option quiet
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
	printf(" %3s %10s %15s    %15s %8s %6s\n", "CPU", "DELTA(us)",
	    "SOURCE", "DEST", "INT", "BYTES");
	last = timestamp;
}

ip:::send
{
	this->delta = (timestamp - last) / 1000;
	printf(" %3d %10d %15s -> %15s %8s %6d\n", cpu, this->delta,
	    args[2]->ip_saddr, args[2]->ip_daddr, args[3]->if_name,
	    args[2]->ip_plength);
	last = timestamp;
}

ip:::receive
{
	this->delta = (timestamp - last) / 1000;
	printf(" %3d %10d %15s <- %15s %8s %6d\n", cpu, this->delta,
	    args[2]->ip_daddr, args[2]->ip_saddr, args[3]->if_name,
	    args[2]->ip_plength);
	last = timestamp;
}
