#!/usr/sbin/dtrace -s

#pragma D option quiet
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
	printf("%-8s %-16s %-18s %5s %3s %s\n", "TIME(ms)", "DATABASE",
	    "USER@HOST", "ms", "RET", "QUERY");
	timezero = timestamp;
}

mysql*:::query-start
{
	self->query = copyinstr(arg0);
	self->db = copyinstr(arg2);
	self->who = strjoin(copyinstr(arg3), strjoin("@", copyinstr(arg4)));
	self->start = timestamp;
}

mysql*:::query-done
/self->start/
{
	this->now = (timestamp - timezero) / 1000000;
	this->time = (timestamp - self->start) / 1000000;
	printf("%-8d %-16.16s %-18.18s %5d %3d %s\n", this->now, self->db,
	    self->who, this->time, (int)arg0, self->query);
	self->start = 0; self->query = 0; self->db = 0; self->who = 0;
}
