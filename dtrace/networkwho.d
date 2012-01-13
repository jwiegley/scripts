#!/usr/sbin/dtrace -s

#pragma D option defaultargs
#pragma D option switchrate=10hz

dtrace:::BEGIN
/$1 == 0/
{
	printf("USAGE: networkwho.d PID\n");
	exit(1);
}

syscall::connect:entry,
syscall::listen:entry
/pid == $1/
{
	ustack();
}

syscall::write*:entry,
syscall::send*:entry
/pid == $1/
{
	trace(fds[arg0].fi_fs);
	ustack();
}
