#!/usr/sbin/dtrace -s

#pragma D option quiet

fbt::segkmem_xalloc:entry
{
	@segkmem_alloc[args[0]->vm_name, arg2] = count();
}
fbt::segkmem_free_vn:entry
{
	@segkmem_free[args[0]->vm_name, arg2] = count();
}
END
{
	printf("%-16s %-8s %-8s %-8s\n",
	    "VMEM NAME", "SIZE", "ALLOCS", "FREES");
	printa("%-16s %-8d %-@8d %-@8d\n", @segkmem_alloc, @segkmem_free);
}
