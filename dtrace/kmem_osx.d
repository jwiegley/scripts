#!/usr/sbin/dtrace -s

#pragma D option quiet

fbt::kmem_alloc:entry
{
	@alloc[arg2] = count();
}
fbt::kmem_free:entry
{
	@free[arg2] = count();
}
END
{
	printf("%-16s %-8s %-8s\n", "SIZE", "ALLOCS", "FREES");
	printa("%-16d %-@8d %-@8d\n", @alloc, @free);
}
