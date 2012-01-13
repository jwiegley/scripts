#!/usr/sbin/dtrace -s

profile:::profile-1001
/execname == $$1/
{
	@["\n  on-cpu (count @1001hz):", ustack()] = count();
}
