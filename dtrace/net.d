#!/usr/sbin/dtrace -s

#pragma D option quiet

syscall::*read:entry,
syscall::*write:entry
/fds[arg0].fi_fs == "sockfs"/
{
	@ior[probefunc] = count();
	@net_bytes[probefunc] = sum(arg2);
}
tick-1sec
{
	printf("%-8s %-16s %-16s\n", "FUNC", "OPS PER SEC", "BYTES PER SEC");
	printa("%-8s %-@16d %-@16d\n", @ior, @net_bytes);
	trunc(@ior); trunc(@net_bytes);
	printf("\n");
}
