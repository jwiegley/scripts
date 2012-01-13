#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	trace("Tracing NFSv3 client file reads... Hit Ctrl-C to end.\n");
}

fbt::nfs3_read:entry
{
	this->path = args[0]->v_path;
	this->bytes = args[1]->uio_resid;
	@r[this->path ? stringof(this->path) : "<null>"] = sum(this->bytes);
}

fbt::nfs3_directio_read:entry
{
	this->path = args[0]->v_path;
	this->bytes = args[1]->uio_resid;
	@n[this->path ? stringof(this->path) : "<null>"] = sum(this->bytes);
}

fbt::nfs3_getpage:entry
{
	this->path = args[0]->v_path;
	this->bytes = arg2;
	@n[this->path ? stringof(this->path) : "<null>"] = sum(this->bytes);
}

dtrace:::END
{
	printf(" %-56s %10s %10s\n", "FILE", "READ(B)", "NET(B)");
	printa(" %-56s %@10d %@10d\n", @r, @n);
}
