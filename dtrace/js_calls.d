#!/usr/sbin/dtrace -Zs

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing JavaScript... Hit Ctrl-C to end.\n");
}

javascript*:::function-entry
{
	this->name = copyinstr(arg2);
	@calls[basename(copyinstr(arg0)), "func", this->name] = count();
}

javascript*:::execute-start
{
	this->filename = basename(copyinstr(arg0));
	@calls[this->filename, "exec", "."] = count();
}

javascript*:::object-create-start
{
	this->name = copyinstr(arg1);
	this->filename = basename(copyinstr(arg0));
	@calls[this->filename, "obj-new", this->name] = count();
}

javascript*:::object-finalize
{
	this->name = copyinstr(arg1);
	@calls["<null>", "obj-free", this->name] = count();
}

dtrace:::END
{
	printf(" %-24s %-10s %-30s %8s\n", "FILE", "TYPE", "NAME", "CALLS");
	printa(" %-24s %-10s %-30s %@8d\n", @calls);
}
