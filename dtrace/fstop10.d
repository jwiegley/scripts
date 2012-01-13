#!/usr/sbin/dtrace -qs

fsinfo:::
{
	@[execname, probefunc] = count();
}
END
{
	trunc(@, 10);
	printf("%-16s %-16s %-8s\n", "EXEC", "FS FUNC", "COUNT");
	printa("%-16s %-16s %-@8d\n", @);
}
