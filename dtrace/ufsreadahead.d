#!/usr/sbin/dtrace -s

fbt::ufs_getpage:entry
{
	@["UFS read (bytes)"] = sum(arg2);
}

fbt::ufs_getpage_ra:return
{
	@["UFS read ahead (bytes)"] = sum(arg1);
}
