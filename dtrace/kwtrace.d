#!/usr/sbin/dtrace -s

#pragma D option flowindent

syscall::write:entry
/fds[arg0].fi_fs == $$1/
{
	self->flag = 1;
}
fbt:::
/self->flag/
{
}
syscall::write:return
/self->flag/
{
	self->flag = 0;
	exit(0);
}
