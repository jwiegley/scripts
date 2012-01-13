#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	trace("Tracing tmpfs disk read time (us):\n");
}

fbt::tmp_getpage:entry
{
	self->vp = args[0];
	self->start = timestamp;
}

fbt::tmp_getpage:return
/self->start/
{
	@[execname, stringof(self->vp->v_path)] =
	    quantize((timestamp - self->start) / 1000);
	self->vp = 0;
	self->start = 0;
}
