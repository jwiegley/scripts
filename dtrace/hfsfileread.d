#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	trace("Tracing HFS+ file reads... Hit Ctrl-C to end.\n");
}

fbt::hfs_vnop_read:entry
{
	this->read = (struct vnop_read_args *)arg0;
	this->path = this->read->a_vp->v_name;
	this->bytes = this->read->a_uio->uio_resid_64;
	@r[this->path ? stringof(this->path) : "<null>"] = sum(this->bytes);
}

fbt::hfs_vnop_strategy:entry
/((struct vnop_strategy_args *)arg0)->a_bp->b_flags & B_READ/
{
	this->strategy = (struct vnop_strategy_args *)arg0;
	this->path = this->strategy->a_bp->b_vp->v_name;
	this->bytes = this->strategy->a_bp->b_bcount;
	@s[this->path ? stringof(this->path) : "<null>"] = sum(this->bytes);
}

dtrace:::END
{
	printf(" %-56s %10s %10s\n", "FILE", "READ(B)", "DISK(B)");
	printa(" %-56s %@10d %@10d\n", @r, @s);
}
