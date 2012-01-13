#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Sampling at 1001 Hertz... Hit Ctrl-C to end.\n");
}

profile:::profile-1001hz
{
	@["System wide disp queue length:"] =
	    sum(curthread->t_cpu->cpu_disp->disp_nrunnable);
}

profile:::tick-1sec
{
	normalize(@, 1001);
	printa(@);
	trunc(@);
}
