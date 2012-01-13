#!/usr/sbin/dtrace -s

#pragma D option quiet

syscall::write:entry
/fds[arg0].fi_fs == "nfs4"/
{
	self->st = timestamp;
}
fbt::$1:entry
/self->st/
{
	self->kst[probefunc] = timestamp;
}
fbt::$1:return
/self->kst[probefunc]/
{
	@ktime[probefunc] = sum(timestamp - self->kst[probefunc]);
	self->kst[probefunc] = 0;
}
syscall::write:return
/self->st/
{
	@write_syscall_time = sum(timestamp - self->st);
	self->st = 0;
	exit(0);
}
END
{
	printa("Write syscall: %@d (nanoseconds)\n", @write_syscall_time);
	printa("Kernel function %s() time: %@d (nanoseconds)\n", @ktime);
}
