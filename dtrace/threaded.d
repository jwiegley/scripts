#!/usr/sbin/dtrace -s

#pragma D option quiet

profile:::profile-101
/pid != 0/
{
	@sample[pid, execname] = lquantize(tid, 0, 128, 1);
}

profile:::tick-1sec
{
	printf("%Y,\n", walltimestamp);
	printa("\n @101hz   PID: %-8d CMD: %s\n%@d", @sample);
	printf("\n");
	trunc(@sample);
}
