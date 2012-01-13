#!/usr/sbin/dtrace -s

#pragma D option quiet
#pragma D option destructive

inline int ALLOWED_UID = 517;

dtrace:::BEGIN
{
	printf("Watching setuid(), allowing only uid %d...\n", ALLOWED_UID);
}

/*
 * Kill setuid() processes who are becomming root, from non-root, and who
 * are not the allowed UID.
 */
syscall::setuid:entry
/arg0 == 0 && curpsinfo->pr_uid != 0 && curpsinfo->pr_uid != ALLOWED_UID/
{
	printf("%Y KILLED %s %d -> %d\n", walltimestamp, execname,
	    curpsinfo->pr_uid, arg0);
	raise(9);
}
