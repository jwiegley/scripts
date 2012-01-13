#!/usr/sbin/dtrace -Zs

#pragma D option quiet
#pragma D option switchrate=10

self int depth;

dtrace:::BEGIN
{
	printf("%s %6s %10s  %16s:%-4s %-8s -- %s\n", "C", "PID", "DELTA(us)",
	    "FILE", "LINE", "TYPE", "SUB");
}

perl*:::sub-entry,
perl*:::sub-return
/self->last == 0/
{
	self->last = timestamp;
}

perl*:::sub-entry
{
	this->delta = (timestamp - self->last) / 1000;
	printf("%d %6d %10d  %16s:%-4d %-8s %*s-> %s\n", cpu, pid, this->delta,
	    basename(copyinstr(arg1)), arg2, "sub", self->depth * 2, "",
	    copyinstr(arg0));
	self->depth++;
	self->last = timestamp;
}

perl*:::sub-return
{
	this->delta = (timestamp - self->last) / 1000;
	self->depth -= self->depth > 0 ? 1 : 0;
	printf("%d %6d %10d  %16s:%-4d %-8s %*s<- %s\n", cpu, pid, this->delta,
	    basename(copyinstr(arg1)), arg2, "sub", self->depth * 2, "",
	copyinstr(arg0));
	self->last = timestamp;
}
