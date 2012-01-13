#!/usr/sbin/dtrace -Zs

#pragma D option quiet
#pragma D option switchrate=10

self int depth;

dtrace:::BEGIN
{
	printf("%s %6s %10s  %16s:%-4s %-8s -- %s\n", "C", "PID", "DELTA(us)",
	    "FILE", "LINE", "TYPE", "NAME");
}

ruby*:::function-entry,
ruby*:::function-return
/self->last == 0/
{
	self->last = timestamp;
}

ruby*:::function-entry
{
	this->delta = (timestamp - self->last) / 1000;
	this->name = strjoin(strjoin(copyinstr(arg0), "::"), copyinstr(arg1));
	printf("%d %6d %10d  %16s:%-4d %-8s %*s-> %s\n", cpu, pid, this->delta,
	    basename(copyinstr(arg2)), arg3, "method", self->depth * 2, "",
	    this->name);
	self->depth++;
	self->last = timestamp;
}

ruby*:::function-return
{
	this->delta = (timestamp - self->last) / 1000;
	self->depth -= self->depth > 0 ? 1 : 0;
	this->name = strjoin(strjoin(copyinstr(arg0), "::"), copyinstr(arg1));
	printf("%d %6d %10d  %16s:%-4d %-8s %*s<- %s\n", cpu, pid, this->delta,
	    basename(copyinstr(arg2)), arg3, "method", self->depth * 2, "",
	this->name);
	self->last = timestamp;
}
