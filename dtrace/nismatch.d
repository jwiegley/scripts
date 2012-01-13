#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("%-20s  %-16s %-16s %s\n", "TIME", "DOMAIN", "MAP", "KEY");
}

pid$target::ypset_current_map:entry
{
	self->map = copyinstr(arg0);
	self->domain = copyinstr(arg1);
}

pid$target::finddatum:entry
/self->map != NULL/
{
	printf("%-20Y  %-16s %-16s %S\n", walltimestamp, self->domain,
	    self->map, copyinstr(arg1));
}
