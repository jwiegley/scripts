#! /usr/sbin/dtrace -qs

syscall::read:entry,
syscall::write:entry
/fds[arg0].fi_fs == "sockfs"/
{
	self->flag = 1
}
syscall::read:return,
syscall::write:return
/(int)arg0 != -1 && self->flag/
{
	@[probefunc] = sum(arg0);
}
syscall::read:return,
syscall::write:return
{
	self->flag = 0;
}
