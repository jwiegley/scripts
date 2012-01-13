#!/usr/sbin/dtrace -qs

self int endds;

syscall::brk:entry
/pid == $target && !self->endds/
{
	self->endds = arg0;
}

syscall::brk:entry
/pid == $target && self->endds != arg0/
{
	printf("Allocated %d\n", arg0 - self->endds);
	self->endds = arg0;
}
