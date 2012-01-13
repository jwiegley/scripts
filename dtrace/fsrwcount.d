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
	@[fds[arg0].fi_fs, probefunc, fds[arg0].fi_mount] = count();
}

dtrace:::END
{
	printf("  %-9s  %-16s %-40s %7s\n", "FS", "SYSCALL", "MOUNTPOINT",
	    "COUNT");
	printa("  %-9.9s  %-16s %-40s %@7d\n", @);
}
