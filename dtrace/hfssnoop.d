#!/usr/sbin/dtrace -s

#pragma D option quiet
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
	printf("%-12s %6s %6s %-12.12s %-14s %-4s %s\n", "TIME(ms)", "UID",
	    "PID", "PROCESS", "CALL", "KB", "FILE");
}

/* see bsd/hfs/hfs_vnops.c */

fbt::hfs_vnop_read:entry
{
	this->read = (struct vnop_read_args *)arg0;
	self->path = this->read->a_vp->v_name;
	self->kb = this->read->a_uio->uio_resid_64 / 1024;
}

fbt::hfs_vnop_write:entry
{
	this->write = (struct vnop_write_args *)arg0;
	self->path = this->write->a_vp->v_name;
	self->kb = this->write->a_uio->uio_resid_64 / 1024;
}

fbt::hfs_vnop_read:entry, fbt::hfs_vnop_write:entry
{
	printf("%-12d %6d %6d %-12.12s %-14s %-4d %s\n", timestamp / 1000000,
	    uid, pid, execname, probefunc, self->kb,
	    self->path != NULL ? stringof(self->path) : "<null>");
	self->path = 0; self->kb = 0;
}
