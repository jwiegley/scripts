#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	trace("Tracing syscall errors... Hit Ctrl-C to end.\n");
}

syscall::read*:entry,
syscall::write*:entry
{ self->fd = arg0; }

syscall::open*:entry,
syscall::stat*:entry
{ self->ptr = arg0; }

syscall::read*:return,
syscall::write*:return
/(int)arg0 < 0 && self->fd > 2/
{
	self->path = fds[self->fd].fi_pathname;
}

syscall::open*:return,
syscall::stat*:return
/(int)arg0 < 0 && self->ptr/
{
	self->path = copyinstr(self->ptr);
}

syscall::read*:return,
syscall::write*:return,
syscall::open*:return,
syscall::stat*:return
/(int)arg0 < 0 && self->path != NULL/
{
	@[execname, probefunc, errno, self->path] = count();
	self->path = 0;
}

syscall::read*:return,
syscall::write*:return
{ self->fd = 0; }

syscall::open*:return,
syscall::stat*:return
{ self->ptr = 0; }

dtrace:::END
{
	printf("%16s %16s %3s %8s %s\n", "PROCESSES", "SYSCALL", "ERR",
	    "COUNT", "PATH");
	printa("%16s %16s %3d %@8d %s\n", @);
}
