#!/usr/sbin/dtrace -s

#pragma D option quiet
#pragma D option switchrate=10

dtrace:::BEGIN
{
	printf(" %3s %12s  %-20s    %-20s\n", "CPU", "DELTA(us)", "OLD", "NEW");
	last = timestamp;
}

tcp:::state-change
{
	this->elapsed = (timestamp - last) / 1000;
	printf(" %3d %12d  %-20s -> %-20s\n", cpu, this->elapsed,
	    tcp_state_string[args[5]->tcps_state],
	    tcp_state_string[args[3]->tcps_state]);
	last = timestamp;
}
