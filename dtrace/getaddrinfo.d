#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("%-20s  %-12s %s\n", "TIME", "LATENCY(ms)", "HOST");
}

pid$target::getaddrinfo:entry
{
	self->host = copyinstr(arg0);
	self->start = timestamp;
}

pid$target::getaddrinfo:return
/self->start/
{
	this->delta = (timestamp - self->start) / 1000000;
	printf("%-20Y  %-12d %s\n", walltimestamp, this->delta, self->host);
	self->host = 0;
	self->start = 0;
}
