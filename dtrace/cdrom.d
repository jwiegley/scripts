#!/usr/sbin/dtrace -Zs

#pragma D option quiet
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
	trace("Tracing hsfs (cdrom) mountfs...\n");
}

fbt::hs_mountfs:entry
{
	printf("%Y:  Mounting %s... ", walltimestamp, stringof(arg2));
	self->start = timestamp;
}

fbt::hs_mountfs:return
/self->start/
{
	this->time = (timestamp - self->start) / 1000000;
	printf("result: %d%s, time: %d ms\n", arg1,
	    arg1 ? "" : " (SUCCESS)", this->time);
	self->start = 0;
}
