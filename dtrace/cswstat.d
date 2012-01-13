#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	/* print header */
	printf("%-20s  %8s %12s %12s\n", "TIME", "NUM", "CSWTIME(us)",
	    "AVGTIME(us)");
	times = 0;
	num = 0;
}

sched:::off-cpu
{
	/* csw start */
	num++;
	start[cpu] = timestamp;
}

sched:::on-cpu
/start[cpu]/
{
	/* csw end */
	times += timestamp - start[cpu];
	start[cpu] = 0;
}

profile:::tick-1sec
{
	/* print output */
	printf("%20Y  %8d %12d %12d\n", walltimestamp, num, times/1000,
	    num == 0 ? 0 : times/(1000 * num));
	times = 0;
	num = 0;
}
