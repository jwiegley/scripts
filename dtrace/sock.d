#!/usr/sbin/dtrace -s

#pragma D option quiet

fbt:sockfs::entry
{
	@[execname, probefunc] = count();
}
END
{
	printf("%-16s %-24s %-8s\n", "EXEC", "SOCKFS FUNC", "COUNT");
	printa("%-16s %-24s %-@8d\n", @);
}
