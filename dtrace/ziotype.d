#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	/* see /usr/include/sys/fs/zfs.h */
	ziotype[0] = "null";
	ziotype[1] = "read";
	ziotype[2] = "write";
	ziotype[3] = "free";
	ziotype[4] = "claim";
	ziotype[5] = "ioctl";
	trace("Tracing ZIO...  Output interval 5 seconds, or Ctrl-C.\n");
}

fbt::zio_create:return
/args[1]->io_type/		/* skip null */
{
	@[stringof(args[1]->io_spa->spa_name),
	    ziotype[args[1]->io_type] != NULL ?
	    ziotype[args[1]->io_type] : "?"] = count();
}

profile:::tick-5sec,
dtrace:::END
{
	printf("\n %-32s %-10s %10s\n", "POOL", "ZIO_TYPE", "CREATED");
	printa(" %-32s %-10s %@10d\n", @);
	trunc(@);
}
