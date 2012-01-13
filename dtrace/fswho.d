#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing... Hit Ctrl-C to end.\n");
}

fsinfo:::read,
fsinfo:::write
{
	@[execname, probename == "read" ? "R" : "W", args[0]->fi_fs,
	    args[0]->fi_mount] = sum(arg1);
}

dtrace:::END
{
	normalize(@, 1024);
	printf("  %-16s  %1s %12s  %-10s %s\n", "PROCESSES", "D", "KBYTES",
	    "FS", "MOUNTPOINT");
	printa("  %-16s  %1.1s %@12d  %-10s %s\n", @);
}
