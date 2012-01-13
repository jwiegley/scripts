#!/usr/sbin/dtrace -s

#pragma D option quiet
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
	printf("%-20s %10s  %s\n", "TIME", "LAT(us)", "FTP CMD");
}

/* on this proftpd version, pr_netio_telnet_gets() returns the FTP cmd */
pid$target:proftpd:pr_netio_telnet_gets:return
{
	self->cmd = copyinstr(arg1);
	self->start = timestamp;
}

pid$target:proftpd:pr_netio_telnet_gets:entry
/self->start/
{
	this->delta = (timestamp - self->start) / 1000;
	/* self->cmd already contains "\r\n" */
	printf("%-20Y %10d  %s", walltimestamp, this->delta, self->cmd);
	self->start = 0;
	self->cmd = 0;
}
