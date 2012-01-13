#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing... Hit Ctrl-C to end.\n");
}

io:::start
{
	this->size = args[0]->b_bcount;
	@Size[pid, curpsinfo->pr_psargs] = quantize(this->size);
}

dtrace:::END
{
	printf("\n%8s  %s\n", "PID", "CMD");
	printa("%8d  %S\n%@d\n", @Size);
}
