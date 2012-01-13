#!/usr/sbin/dtrace -s

#pragma D option quiet
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
	printf("%6s %-16s %s\n", "PID", "PROCESS", "INODE MISS PATH");
}

fbt::ufs_lookup:entry
{
	self->dvp = args[0];
	self->name = arg1;
}

fbt::ufs_lookup:return
{
	self->dvp = 0;
	self->name = 0;
}

fbt::ufs_alloc_inode:entry
/self->dvp && self->name/
{
	printf("%6d %-16s %s/%s\n", pid, execname,
	    stringof(self->dvp->v_path), stringof(self->name));
}
