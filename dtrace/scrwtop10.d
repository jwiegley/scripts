#!/usr/sbin/dtrace -s

#pragma D option quiet

syscall::*read*:entry,
syscall::*write*:entry
{
	@[execname, probefunc, fds[arg0].fi_fs] = count();
}
END
{
	trunc(@, 10);
	printf("%-16s %-16s %-8s %-8s\n", "EXEC", "SYSCALL", "FS", "COUNT");
	printa("%-16s %-16s %-8s %-@8d\n", @);
}
