#!/usr/sbin/dtrace -Zs

/* increasing bufsize can reduce drops */
#pragma D option bufsize=16m
#pragma D option quiet
#pragma D option switchrate=10

self int depth[int];

dtrace:::BEGIN
{
	printf("%3s %6s %-16s -- %s\n", "C", "PID", "TIME(us)", "CLASS.METHOD");
}

hotspot*:::method-entry
{
	this->class = (char *)copyin(arg1, arg2 + 1);
	this->class[arg2] = '\0';
	this->method = (char *)copyin(arg3, arg4 + 1);
	this->method[arg4] = '\0';

	printf("%3d %6d %-16d %*s-> %s.%s\n", cpu, pid, timestamp / 1000,
	    self->depth[arg0] * 2, "", stringof(this->class),
	stringof(this->method));
	self->depth[arg0]++;
}

hotspot*:::method-return
{
	this->class = (char *)copyin(arg1, arg2 + 1);
	this->class[arg2] = '\0';
	this->method = (char *)copyin(arg3, arg4 + 1);
	this->method[arg4] = '\0';

	self->depth[arg0] -= self->depth[arg0] > 0 ? 1 : 0;
	printf("%3d %6d %-16d %*s<- %s.%s\n", cpu, pid, timestamp / 1000,
	    self->depth[arg0] * 2, "", stringof(this->class),
	stringof(this->method));
}
