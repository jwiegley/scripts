#!/usr/sbin/dtrace -s

#pragma D option quiet
#pragma D option defaultargs
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
	printf("%-8s %5s %5s %5s %s\n", "TIMEms", "QRYms", "EXCms", "CPUms",
	    "QUERY");
	min_ns = $1 * 1000000;
	timezero = timestamp;
}

postgresql*:::query-start
{
	self->start = timestamp;
	self->vstart = vtimestamp;
}

postgresql*:::query-execute-start
{
	self->estart = timestamp;
}

postgresql*:::query-execute-done
/self->estart/
{
	self->exec = timestamp - self->estart;
	self->estart = 0;
}

postgresql*:::query-done
/self->start && (timestamp - self->start) >= min_ns/
{
	this->now = (timestamp - timezero) / 1000000;
	this->time = (timestamp - self->start) / 1000000;
	this->vtime = (vtimestamp - self->vstart) / 1000000;
	this->etime = self->exec / 1000000;
	printf("%-8d %5d %5d %5d %s\n", this->now, this->time, this->etime,
	    this->vtime, copyinstr(arg0));
}

postgresql*:::query-done
{
	self->start = 0; self->vstart = 0; self->exec = 0;
}
