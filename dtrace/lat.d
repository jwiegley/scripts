#!/usr/sbin/dtrace -s
#pragma D option quiet
sched:::enqueue
{
	s[args[0]->pr_lwpid, args[1]->pr_pid] = timestamp;
}

sched:::dequeue
/this->start = s[args[0]->pr_lwpid, args[1]->pr_pid]/
{
	this->time = timestamp - this->start;
	@lat_avg[args[2]->cpu_id] = avg(this->time);
	@lat_max[args[2]->cpu_id] = max(this->time);
	@lat_min[args[2]->cpu_id] = min(this->time);
	s[args[0]->pr_lwpid, args[1]->pr_pid] = 0;

}
tick-1sec
{
	printf("%-8s %-12s %-12s %-12s\n",
	    "CPU", "AVG(ns)", "MAX(ns)", "MIN(ns)");
	printa("%-8d %-@12d %-@12d %-@12d\n", @lat_avg, @lat_max, @lat_min);
	trunc(@lat_avg); trunc(@lat_max); trunc(@lat_min);
}
