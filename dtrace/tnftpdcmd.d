#!/usr/sbin/dtrace -s

#pragma D option quiet
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
	printf("%-20s %10s  %s\n", "TIME", "LAT(us)", "FTP CMD");
}

pid$target:ftpd:getline:return
/arg1 && arg1 != 1/
{
	self->line = copyinstr(arg1);
	self->start = timestamp;
}

pid$target:ftpd:getline:entry
/self->start/
{
	this->delta = (timestamp - self->start) / 1000;
	/* self->line already contains "\r\n" */
	printf("%-20Y %10d  %s", walltimestamp, this->delta, self->line);
	self->start = 0;
	self->line = 0;
}
