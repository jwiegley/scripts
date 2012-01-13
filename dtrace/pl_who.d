#!/usr/sbin/dtrace -Zs

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing... Hit Ctrl-C to end.\n");
}

perl*:::sub-entry
{
	@lines[pid, uid, copyinstr(arg1)] = count();
}

dtrace:::END
{
	printf("   %6s %6s %6s %s\n", "PID", "UID", "SUBS", "FILE");
	printa("   %6d %6d %@6d %s\n", @lines);
}
