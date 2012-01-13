#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN { trace("Tracing...Ouput after 10 seconds, or Ctrl-C\n"); }

fbt:unix:pagefault:entry
{
	@st[execname] = count();
	self->pfst = timestamp
}
fbt:unix:pagefault:return
/self->pfst/
{
	@pft[execname] = sum(timestamp - self->pfst);
	self->pfst = 0;
}
tick-10s
{
	printf("Pagefault counts by execname ...\n");
	printa(@st);

	printf("\nPagefault times(ns) by execname...\n");
	printa(@pft);

	trunc(@st);
	trunc(@pft);
}
