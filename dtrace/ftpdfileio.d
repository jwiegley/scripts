#!/usr/sbin/dtrace -Zs

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing... Hit Ctrl-C to end.\n");
}

ftp*:::transfer-done
{
	@[args[1]->fti_cmd, args[1]->fti_pathname] = sum(args[1]->fti_nbytes);
}

dtrace:::END
{
	printf("\n%8s %12s  %s\n", "DIR", "BYTES", "PATHNAME");
	printa("%8s %@12d  %s\n", @);
}
