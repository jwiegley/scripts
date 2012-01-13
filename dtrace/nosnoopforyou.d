#!/usr/sbin/dtrace -Cs

#pragma D option quiet
#pragma D option destructive

/* /usr/include/sys/dlpi.h: */
#define	DL_PROMISCON_REQ	0x1f

dtrace:::BEGIN
{
	trace("Preventing promiscuity...\n");
}

fbt::dld_wput_nondata:entry
{
	this->mp = args[1];
	this->prim = ((union DL_primitives *)this->mp->b_rptr)->dl_primitive;
}

fbt::dld_wput_nondata:entry
/this->prim == DL_PROMISCON_REQ/
{
	printf("%Y KILLED %s PID:%d PPID:%d\n", walltimestamp, execname,
	    pid, ppid);
	/* raise(9); */
}
