#!/usr/sbin/dtrace -Cs

#pragma D option quiet

#define	PRINT_HDR printf("%-8s %-16s %-8s %-16s\n",
	"RPS", "RD BYTES", "WPS", "WR BYTES");

dtrace:::BEGIN
{
	PRINT_HDR
}

io:::start
/execname == $$1 && args[0]->b_flags & B_READ/
{
	@rps = count();
	@rbytes = sum(args[0]->b_bcount);
}

io:::start
/execname == $$1 && args[0]->b_flags & B_WRITE/
{
	@wps = count();
	@wbytes = sum(args[0]->b_bcount);
}
tick-1sec
{
	printa("%-@8d %-@16d %-@8d %-@16d\n", @rps, @rbytes, @wps, @wbytes);
	trunc(@rps); trunc(@rbytes); trunc(@wps); trunc(@wbytes);
}
tick-1sec
/x++ == 20/
{
	PRINT_HDR
	x = 0;
}
