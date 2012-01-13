#!/usr/sbin/dtrace -Zs

#pragma D option quiet
#pragma D option switchrate=10

self int depth;

dtrace:::BEGIN
{
	printf("%s %6s %10s  %16s:%-4s %-8s -- %s\n", "C", "PID", "DELTA(us)",
	    "FILE", "LINE", "TYPE", "FUNC");
}

python*:::function-entry,
python*:::function-return
/self->last == 0/
{
	self->last = timestamp;
}

python*:::function-entry
{
	this->delta = (timestamp - self->last) / 1000;
	printf("%d %6d %10d  %16s:%-4d %-8s %*s-> %s\n", cpu, pid, this->delta,
	    basename(copyinstr(arg0)), arg2, "func", self->depth * 2, "",
	    copyinstr(arg1));
	self->depth++;
	self->last = timestamp;
}

python*:::function-return
{
	this->delta = (timestamp - self->last) / 1000;
	self->depth -= self->depth > 0 ? 1 : 0;
	printf("%d %6d %10d  %16s:%-4d %-8s %*s<- %s\n", cpu, pid, this->delta,
	    basename(copyinstr(arg0)), arg2, "func", self->depth * 2, "",
	    copyinstr(arg1));
	self->last = timestamp;
}
