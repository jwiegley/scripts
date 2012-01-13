#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing... Hit Ctrl-C to end.\n");
}

fbt::dnlc_lookup:return
{
	this->code = arg1 == 0 ? 0 : 1;
	@Result[execname, pid] = lquantize(this->code, 0, 1, 1);
}

dtrace:::END
{
	printa(" CMD: %-16s PID: %d\n%@d\n", @Result);
}
