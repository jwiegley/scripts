#!/usr/sbin/dtrace -s

#pragma D option quiet
#pragma D option defaultargs
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
	printf("%-20s  %-8s %-8s %-8.8s %s\n", "TIME", "UID", "PID",
	    "ACTION", "ARGS");
	my_sshd = $1;
}

syscall::write*:entry
/execname == "sshd" && fds[arg0].fi_fs == "sockfs" && pid != my_sshd/
{
	printf("%-20Y  %-8d %-8d %-8.8s %d bytes\n", walltimestamp, uid, pid,
	    probefunc, arg2);
}

syscall::accept*:return
/execname == "sshd"/
{
	printf("%-20Y  %-8d %-8d %-8.8s %s\n", walltimestamp, uid, pid,
	    probefunc, "CONNECTION STARTED");
}
