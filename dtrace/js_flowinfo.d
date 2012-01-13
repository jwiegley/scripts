#!/usr/sbin/dtrace -Zs

#pragma D option quiet
#pragma D option switchrate=10

self int depth;

dtrace:::BEGIN
{
	printf("%3s %6s %10s  %16s:%-4s %-8s -- %s\n", "C", "PID", "DELTA(us)",
	    "FILE", "LINE", "TYPE", "FUNC");
}

javascript*:::function-info,
javascript*:::function-return
/self->last == 0/
{
	self->last = timestamp;
}

javascript*:::function-info
{
	this->delta = (timestamp - self->last) / 1000;
	printf("%3d %6d %10d  %16s:%-4d %-8s %*s-> %s\n", cpu, pid,
	    this->delta, basename(copyinstr(arg4)), arg5, "func",
	self->depth * 2, "", copyinstr(arg2));
	self->depth++;
	self->last = timestamp;
}

javascript*:::function-return
{
	this->delta = (timestamp - self->last) / 1000;
	self->depth -= self->depth > 0 ? 1 : 0;
	printf("%3d %6d %10d  %16s:-    %-8s %*s<- %s\n", cpu, pid,
	    this->delta, basename(copyinstr(arg0)), "func", self->depth * 2,
	    "", copyinstr(arg2));
	self->last = timestamp;
}
