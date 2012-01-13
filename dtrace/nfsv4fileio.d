#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	trace("Tracing... Hit Ctrl-C to end.\n");
}

nfsv4:::op-read-done
{
	@readbytes[args[1]->noi_curpath] = sum(args[2]->data_len);
}

nfsv4:::op-write-done
{
	@writebytes[args[1]->noi_curpath] = sum(args[2]->count);
}

dtrace:::END
{
	printf("\n%12s %12s  %s\n", "Rbytes", "Wbytes", "Pathname");
	printa("%@12d %@12d  %s\n", @readbytes, @writebytes);
}
