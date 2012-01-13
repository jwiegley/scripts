#!/usr/sbin/dtrace -s

#pragma D option quiet

vminfo:::
{
	@[execname, probefunc, probename] = count();
}
tick-1sec
{
	trunc(@, 10);
	printf("%-16s %-16s %-16s %-8s\n", "EXEC", "FUNCTION", "NAME", "COUNT");
	printa("%-16s %-16s %-16s %-@8d\n", @);
	trunc(@);
	printf("\n");
}
