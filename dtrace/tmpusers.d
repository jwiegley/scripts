#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("%6s %6s %-16s %s\n", "UID", "PID", "PROCESS", "FILE");
}

fbt::tmp_open:entry
{
	printf("%6d %6d %-16s %s\n", uid, pid, execname,
	    stringof((*args[0])->v_path));
}
