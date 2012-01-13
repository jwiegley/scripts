#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing... Hit Ctrl-C to end.\n");
}

self int last[dev_t];

io:::start
/self->last[args[0]->b_edev] != 0/
{
	this->last = self->last[args[0]->b_edev];
	this->dist = (int)(args[0]->b_blkno - this->last) > 0 ?
	    args[0]->b_blkno - this->last : this->last - args[0]->b_blkno;
	@Size[pid, curpsinfo->pr_psargs] = quantize(this->dist);
}

io:::start
{
	self->last[args[0]->b_edev] = args[0]->b_blkno +
	    args[0]->b_bcount / 512;
}

dtrace:::END
{
	printf("\n%8s  %s\n", "PID", "CMD");
	printa("%8d  %S\n%@d\n", @Size);
}
