#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN { trace("Tracing... Output after 10 seconds, or Ctrl-C\n"); }

syscall::$1:entry
/execname == $$2/
{
	self->fd = arg0;
	self->st = timestamp;
}
syscall::$1:return
/self->st/
{
	@iot[pid, probefunc, fds[self->fd].fi_pathname] =
	    sum(timestamp - self->st);
	self->fd = 0;
	self->st = 0;
}
tick-10sec
{
	normalize(@iot, 1000);
	printf("%-8s %-8s %-32s %-16s\n",
	    "PID", "SYSCALL", "PATHNAME", "TIME(us)");
	printa("%-8d %-8s %-32s %-@16d\n", @iot);
}
