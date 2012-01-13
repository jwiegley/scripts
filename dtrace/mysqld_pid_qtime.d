#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing... Hit Ctrl-C to end.\n");
}

pid$target::*dispatch_command*:entry
{
	self->query = copyinstr(arg2);
	self->start = timestamp;
}

pid$target::*dispatch_command*:return
/self->start/
{
	@time[self->query] = quantize(timestamp - self->start);
	self->query = 0; self->start = 0;
}

dtrace:::END
{
	printf("MySQL query execution latency (ns):\n");
	printa(@time);
}
