#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing... Hit Ctrl-C to end.\n");
}

pid$target::exec_simple_query:entry
{
	self->query = copyinstr(arg0);
	self->start = timestamp;
}

pid$target::exec_simple_query:return
/self->start/
{
	@time[self->query] = quantize(timestamp - self->start);
	self->start = 0; self->query = 0;
}

dtrace:::END
{
	printf("PostgreSQL simple query execution latency (ns):\n");
	printa(@time);
}
