#!/usr/sbin/dtrace -s

#pragma D option quiet
inline int MAX = 10;

dtrace:::BEGIN
{
	start = timestamp;
	printf("Tracing for %d seconds...hit Ctrl-C to terminate sooner\n",
	    MAX);
}

sched:::on-cpu
/pid == $target/
{
	self->ts = timestamp;
}

sched:::off-cpu
/self->ts/
{
	@[cpu] = sum(timestamp - self->ts);
	self->ts = 0;
}

profile:::tick-1sec
/++x == MAX/
{
	exit(0);
}

dtrace:::END
{
	printf("\nCPU distribution over %d milliseconds:\n\n",
	    (timestamp - start) / 1000000);
	printf("CPU microseconds\n--- ------------\n");
	normalize(@, 1000);
	printa("%3d %@d\n", @);
}
