#!/usr/sbin/dtrace -s

sched:::off-cpu
/execname == $$1/
{
	self->start = timestamp;
}

sched:::on-cpu
/self->start/
{
	this->delta = (timestamp - self->start) / 1000;
	@["off-cpu (us):", ustack()] = quantize(this->delta);
	self->start = 0;
}
