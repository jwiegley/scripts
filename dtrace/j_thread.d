#!/usr/sbin/dtrace -Zs

#pragma D option quiet
#pragma D option switchrate=10

dtrace:::BEGIN
{
	printf("%-20s  %6s/%-5s -- %s\n", "TIME", "PID", "TID", "THREAD");
}

hotspot*:::thread-start
{
	this->thread = (char *)copyin(arg0, arg1 + 1);
	this->thread[arg1] = '\0';
	printf("%-20Y  %6d/%-5d => %s\n", walltimestamp, pid, tid,
	    stringof(this->thread));
}

hotspot*:::thread-stop
{
	this->thread = (char *)copyin(arg0, arg1 + 1);
	this->thread[arg1] = '\0';
	printf("%-20Y  %6d/%-5d <= %s\n", walltimestamp, pid, tid,
	    stringof(this->thread));
}
