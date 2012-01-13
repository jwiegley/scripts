#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	trace("Tracing NFSv3 client file reads... Hit Ctrl-C to end.\n");
}

fbt::nfs3_read:entry
{
	@q["NFS read size (bytes)"] = quantize(args[1]->uio_resid);
	@s["NFS read (bytes)"] = sum(args[1]->uio_resid);
}

fbt::nfs3_directio_read:entry
{
	@q["NFS network read size (bytes)"] = quantize(args[1]->uio_resid);
	@s["NFS network read (bytes)"] = sum(args[1]->uio_resid);
}

fbt::nfs3_getpage:entry
{
	@q["NFS network read size (bytes)"] = quantize(arg2);
	@s["NFS network read (bytes)"] = sum(arg2);
}
