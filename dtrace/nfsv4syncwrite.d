#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	/* See /usr/include/nfs/nfs4_kprot.h */
	stable_how[0] = "Unstable";
	stable_how[1] = "Data_Sync";
	stable_how[2] = "File_Sync";
	printf("Tracing NFSv4 writes and commits... Hit Ctrl-C to end.\n");
}

nfsv4:::op-write-start
{
	@["write", stable_how[args[2]->stable], args[1]->noi_curpath] = count();
}

nfsv4:::op-commit-start
{
	@["commit", "-", args[1]->noi_curpath] = count();
}

dtrace:::END
{
	printf(" %-7s %-10s %-10s %s\n", "OP", "TYPE", "COUNT", "PATH");
	printa(" %-7s %-10s %@-10d %s\n", @);
}
