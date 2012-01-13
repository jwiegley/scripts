#!/usr/sbin/dtrace -s
#pragma D option flowindent

syscall::$1:entry
{
	self->flag = 1;
}
fbt:::
/self->flag/
{
}
syscall::$1:return
/self->flag/
{
	self->flag = 0;
	exit(0);
}
