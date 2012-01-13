#!/usr/sbin/dtrace -s

sched:::off-cpu
{
	self->start = timestamp;
}

sched:::on-cpu
/self->start/
{
	this->delta = (timestamp - self->start) / 1000;
	@["off-cpu (us):", stack()] = quantize(this->delta);
	self->start = 0;
}
