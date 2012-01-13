#!/usr/sbin/dtrace -Zs

#pragma D option quiet
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
	trace("Tracing udfs (dvd) mountfs...\n");
}

fbt::ud_mountfs:entry
{
	printf("%Y:  Mounting %s... ", walltimestamp, stringof(arg2));
	self->start = timestamp;
}

fbt::ud_mountfs:return
/self->start/
{
	this->time = (timestamp - self->start) / 1000000;
	printf("result: %d%s, time: %d ms\n", arg1,
	    arg1 ? "" : " (SUCCESS)", this->time);
	self->start = 0;
}
