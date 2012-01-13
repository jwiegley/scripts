#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing Socket I/O... Hit Ctrl-C to end.\n");
}

syscall::read*:entry,
syscall::write*:entry,
syscall::send*:entry,
syscall::recv*:entry
/fds[arg0].fi_fs == "sockfs" || fds[arg0].fi_name == "<socket>"/
{
	@[execname, pid, probefunc] = count();
}

dtrace:::END
{
	printf("  %-16s %-8s %-16s %10s\n", "PROCESS", "PID", "SYSCALL",
	    "COUNT");
	printa("  %-16s %-8d %-16s %@10d\n", @);
}
