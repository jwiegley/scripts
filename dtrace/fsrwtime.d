#!/usr/sbin/dtrace -Zs

/* trace read() variants, but not readlink() or __pthread*() (macosx) */
syscall::read:entry,
syscall::readv:entry,
syscall::pread*:entry,
syscall::*read*nocancel:entry,
syscall::*write*:entry
{
	self->fd = arg0;
	self->start = timestamp;
}

syscall::*read*:return,
syscall::*write*:return
/self->start/
{
	this->delta = (timestamp - self->start) / 1000;
	@[fds[self->fd].fi_fs, probefunc, fds[self->fd].fi_mount] =
	    quantize(this->delta);
	self->fd = 0; self->start = 0;
}

dtrace:::END
{
	printa("\n  %s %s (us) \t%s%@d", @);
}
