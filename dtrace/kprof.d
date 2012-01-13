#!/usr/sbin/dtrace -s

profile-997hz
/arg0 && curthread->t_pri != -1/
{
	@[stack()] = count();
}
tick-10sec
{
	trunc(@, 10);
	printa(@);
	exit(0);
}
