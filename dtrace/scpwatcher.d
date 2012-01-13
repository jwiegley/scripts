#!/usr/sbin/dtrace -qs

inline int stdout = 1;

syscall::write:entry
/execname == "scp" && arg0 == stdout/
{
	printf("%s\n", copyinstr(arg1));
}
