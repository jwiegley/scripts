#!/usr/sbin/dtrace -s

#pragma D option quiet

fbt::kmem_cache_alloc:entry
{
	@alloc[args[0]->cache_name] = count();
}
fbt::kmem_cache_free:entry
{
	@free[args[0]->cache_name] = count();
}
tick-1sec
{
	printf("%-32s %-8s %-8s\n", "CACHE NAME", "ALLOCS", "FREES");
	printa("%-32s %-@8d %-@8d\n", @alloc, @free);
	trunc(@alloc); trunc(@free);
}
