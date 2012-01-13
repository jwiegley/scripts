#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	trace("Tracing... Hit Ctrl-C to end.\n");
}

nfsv3:::op-read-done
{
	@readbytes[args[1]->noi_curpath] = sum(args[2]->res_u.ok.data.data_len);
}

nfsv3:::op-write-done
{
	@writebytes[args[1]->noi_curpath] = sum(args[2]->res_u.ok.count);
}

dtrace:::END
{
	printf("\n%12s %12s  %s\n", "Rbytes", "Wbytes", "Pathname");
	printa("%@12d %@12d  %s\n", @readbytes, @writebytes);
}
