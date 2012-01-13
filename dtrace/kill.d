#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("%-6s %12s %6s %-8s %s\n",
	    "FROM", "COMMAND", "SIG", "TO", "RESULT");
}

syscall::kill:entry
{
	self->target = (int)arg0;
	self->signal = arg1;
}

syscall::kill:return
{
	printf("%-6d %12s %6d %-8d %d\n",
	    pid, execname, self->signal, self->target, (int)arg0);
	self->target = 0;
	self->signal = 0;
}
