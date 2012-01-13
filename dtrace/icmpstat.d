#!/usr/sbin/dtrace -s

#pragma D option quiet

mib::icmp_*:
{
	@icmp[probename] = sum(arg0);
}

profile:::tick-1sec
{
	printf("\n%Y:\n\n", walltimestamp);
	printf("  %32s %8s\n", "STATISTIC", "VALUE");
	printa("  %32s %@8d\n", @icmp);
	trunc(@icmp);
}
