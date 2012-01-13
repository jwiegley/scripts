#!/usr/sbin/dtrace -s

#pragma D option quiet

fbt:sockfs::entry
/execname == "java"/
{
	@[probefunc] = count();
	self->st[stackdepth] = timestamp;

}
fbt:sockfs::return
/self->st[stackdepth]/
{
	@sockfs_times[pid, probefunc] = sum(timestamp - self->st[stackdepth]);
	self->st[stackdepth] = 0;
}
tick-1sec
{
	normalize(@sockfs_times, 1000);
	printf("%-8s %-24s %-16s\n", "PID", "SOCKFS FUNC", "TIME(ms)");
	printa("%-8d %-24s %-@16d\n", @sockfs_times);

	printf("\nSOCKFS CALLS PER SECOND:\n");
	printa(@);

	trunc(@); trunc(@sockfs_times);
	printf("\n\n");
}
