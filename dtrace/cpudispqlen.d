#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Sampling at 1001 Hertz... Hit Ctrl-C to end.\n");
}

profile:::profile-1001hz
{
	@["Per-CPU disp queue length:"] =
	    lquantize(curthread->t_cpu->cpu_disp->disp_nrunnable, 0, 64, 1);
}
