#!/usr/sbin/dtrace -Zs

#pragma D option quiet
#pragma D option switchrate=10

self int depth;

dtrace:::BEGIN
{
	printf("%3s %6s %-16s -- %s\n", "C", "PID", "TIME(us)", "PROCEDURE");
}

tcl*:::proc-entry
{
	printf("%3d %6d %-16d %*s-> %s\n", cpu, pid, timestamp / 1000,
	self->depth * 2, "", copyinstr(arg0));
	self->depth++;
}

tcl*:::proc-return
{
	self->depth -= self->depth > 0 ? 1 : 0;
	printf("%3d %6d %-16d %*s<- %s\n", cpu, pid, timestamp / 1000,
	    self->depth * 2, "", copyinstr(arg0));
}
