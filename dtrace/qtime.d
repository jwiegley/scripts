#!/usr/sbin/dtrace -s

sched:::enqueue
{
	a[args[0]->pr_lwpid, args[1]->pr_pid, args[2]->cpu_id] =
	    timestamp;
}

sched:::dequeue
/a[args[0]->pr_lwpid, args[1]->pr_pid, args[2]->cpu_id]/
{
	@[args[2]->cpu_id] = quantize(timestamp -
	    a[args[0]->pr_lwpid, args[1]->pr_pid, args[2]->cpu_id]);
	a[args[0]->pr_lwpid, args[1]->pr_pid, args[2]->cpu_id] = 0;
}
