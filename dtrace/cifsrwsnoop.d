#!/usr/sbin/dtrace -s

#pragma D option quiet
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
	printf("%-16s %-18s %2s %-10s %6s %s\n", "TIME(us)",
	    "CLIENT", "OP", "OFFSET(KB)", "BYTES", "PATHNAME");
}

smb:::op-Read-done, smb:::op-ReadX-done
{
	this->dir = "R";
}

smb:::op-Write-done, smb:::op-WriteX-done
{
	this->dir = "W";
}

smb:::op-Read-done, smb:::op-ReadX-done,
smb:::op-Write-done, smb:::op-WriteX-done
{
	printf("%-16d %-18s %2s %-10d %6d %s\n", timestamp / 1000,
	    args[0]->ci_remote, this->dir, args[2]->soa_offset / 1024,
	    args[2]->soa_count, args[1]->soi_curpath);
}
