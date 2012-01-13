#!/usr/sbin/dtrace -s

fbt::putnext:entry
{
	@[stringof(args[0]->q_qinfo->qi_minfo->mi_idname), stack(5)] = count();
}
