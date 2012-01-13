#!/usr/sbin/dtrace -s

#pragma D option quiet

syscall:::entry
{
	@[execname, probefunc] = count();
}
END
{
	trunc(@, 10);
	printf("%-16s %-16s %-8s\n", "EXEC", "SYSCALL", "COUNT");
	printa("%-16s %-16s %-@8d\n", @);
}
