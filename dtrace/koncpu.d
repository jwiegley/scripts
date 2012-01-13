#!/usr/sbin/dtrace -s

profile:::profile-1001
{
	@["\n  on-cpu stack (count @1001hz):", stack()] = count();
}
