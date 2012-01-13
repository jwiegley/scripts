#!/usr/sbin/dtrace -qs

fsinfo:::
{
	@[execname, probename, args[0]->fi_fs, args[0]->fi_pathname] = count();
}
END
{
	trunc(@, 10);
	printf("%-16s %-8s %-8s %-32s %-8s\n",
	    "EXEC", "FS FUNC", "FS TYPE", "PATH", "COUNT");
	printa("%-16s %-8s %-8s %-32s %-@8d\n", @);
}
