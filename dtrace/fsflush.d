#!/usr/sbin/dtrace -s

#pragma D option quiet

BEGIN
{
	lexam = 0; lscan = 0; llock = 0; lmod = 0; lcoal = 0; lrel = 0;
	ltime = 0;
	printf("%10s %10s %10s %10s %10s %10s %10s\n", "SCANNED", "EXAMINED",
	    "LOCKED", "MODIFIED", "COALESCE", "RELEASES", "TIME(ns)");
}

tick-1s
/lexam/
{
	printf("%10d %10d %10d %10d %10d %10d %10d\n", `fsf_total.fsf_scan,
	    `fsf_total.fsf_examined - lexam, `fsf_total.fsf_locked - llock,
	    `fsf_total.fsf_modified - lmod, `fsf_total.fsf_coalesce - lcoal,
	    `fsf_total.fsf_releases - lrel, `fsf_total.fsf_time - ltime);
	lexam = `fsf_total.fsf_examined;
	lscan = `fsf_total.fsf_scan;
	llock = `fsf_total.fsf_locked;
	lmod = `fsf_total.fsf_modified;
	lcoal = `fsf_total.fsf_coalesce;
	lrel = `fsf_total.fsf_releases;
	ltime = `fsf_total.fsf_time;
}

/*
 * First time through
 */

tick-1s
/!lexam/
{
	lexam = `fsf_total.fsf_examined;
	lscan = `fsf_total.fsf_scan;
	llock = `fsf_total.fsf_locked;
	lmod = `fsf_total.fsf_modified;
	lcoal = `fsf_total.fsf_coalesce;
	ltime = `fsf_total.fsf_time;
	lrel = `fsf_total.fsf_releases;
}
