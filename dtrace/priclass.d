#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Sampling... Hit Ctrl-C to end.\n");
}

profile:::profile-1001hz
{
	@count[stringof(curlwpsinfo->pr_clname)] =
	    lquantize(curlwpsinfo->pr_pri, 0, 170, 10);
}
