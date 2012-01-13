#!/usr/sbin/dtrace -s
#pragma D option quiet
sched:::enqueue
/args[1]->pr_pid == $target/
{
	s[args[2]->cpu_id] = timestamp;
}

sched:::dequeue
/s[args[2]->cpu_id]/
{
	@lat_sum[args[1]->pr_pid] = sum(timestamp - s[args[2]->cpu_id]);
	s[args[2]->cpu_id] = 0;
}

tick-1sec
{
	normalize(@lat_sum, 1000);
	printa("PROCESS: %d spent %@d microseconds waiting for a CPU\n",
	    @lat_sum);
	trunc(@lat_sum);
}
