#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	trace("Tracing... Hit Ctrl-C to end.\n");
}

smb:::op-Read-done, smb:::op-ReadX-done
{
	@readbytes[args[1]->soi_curpath] = sum(args[2]->soa_count);
}

smb:::op-Write-done, smb:::op-WriteX-done
{
	@writebytes[args[1]->soi_curpath] = sum(args[2]->soa_count);
}

dtrace:::END
{
	printf("\n%12s %12s  %s\n", "Rbytes", "Wbytes", "Pathname");
	printa("%@12d %@12d  %s\n", @readbytes, @writebytes);
}
