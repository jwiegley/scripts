#!/usr/sbin/dtrace -Zs

/* trace read() variants, but not readlink() or __pthread*() (macosx) */
syscall::read:entry,
syscall::readv:entry,
syscall::pread*:entry,
syscall::*read*nocancel:entry
{
	self->fd = arg0;
	self->start = timestamp;
}

syscall::*read*:return
/self->start && arg0 > 0/
{
	this->kb = (arg1 / 1024) ? arg1 / 1024 : 1;
	this->ns_per_kb = (timestamp - self->start) / this->kb;
	@[fds[self->fd].fi_fs, probefunc, fds[self->fd].fi_mount] =
	    quantize(this->ns_per_kb);
}

syscall::*read*:return
{
	self->fd = 0; self->start = 0;
}

dtrace:::END
{
	printa("\n  %s %s (ns per kb) \t%s%@d", @);
}
