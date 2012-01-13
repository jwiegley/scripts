#!/usr/sbin/dtrace -Zs

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing... Hit Ctrl-C to end.\n");
}

/* trace read() variants, but not readlink() or __pthread*() (macosx) */
syscall::read:entry,
syscall::readv:entry,
syscall::pread*:entry,
syscall::*read*nocancel:entry,
syscall::*write*:entry
{
	@[execname, probefunc, fds[arg0].fi_mount] = count();
}

dtrace:::END
{
	printf("  %-16s %-16s %-30s %7s\n", "PROCESS", "SYSCALL",
	    "MOUNTPOINT", "COUNT");
	printa("  %-16s %-16s %-30s %@7d\n", @);
}
