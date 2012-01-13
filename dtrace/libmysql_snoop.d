#!/usr/sbin/dtrace -Zs

#pragma D option quiet
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
	printf("%-8s %6s %3s %s\n", "TIME(ms)", "Q(ms)", "RET", "QUERY");
	timezero = timestamp;
}

pid$target::mysql_query:entry,
pid$target::mysql_real_query:entry
{
	self->query = copyinstr(arg1);
	self->start = timestamp;
}

pid$target::mysql_query:return,
pid$target::mysql_real_query:return
/self->start/
{
	this->time = (timestamp - self->start) / 1000000;
	this->now = (timestamp - timezero) / 1000000;
	printf("%-8d %6d %3d %s\n", this->now, this->time, arg1, self->query);
	self->start = 0; self->query = 0;
}
