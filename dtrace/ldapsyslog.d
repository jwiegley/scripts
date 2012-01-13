#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN { printf("Tracing PID %d...\n", $target); }

pid$target::syslog:entry
{
	self->in_syslog = 1;
}

pid$target::strlen:entry
/self->in_syslog/
{
	self->buf = arg0;
}

pid$target::syslog:return
/self->buf/
{
	trace(copyinstr(self->buf));
	self->in_syslog = 0;
	self->buf = 0;
}
