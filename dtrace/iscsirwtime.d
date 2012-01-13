#!/usr/sbin/dtrace -s

#pragma D option quiet

inline int TOP_TARGETS = 10;

dtrace:::BEGIN
{
	printf("Tracing iSCSI target... Hit Ctrl-C to end.\n");
}

iscsi:::xfer-start
{
	start[arg1] = timestamp;
}

iscsi:::xfer-done
/start[arg1] != 0/
{
	this->elapsed = timestamp - start[arg1];
	@rw[arg8 ? "read" : "write"] = quantize(this->elapsed / 1000);
	@host[args[0]->ci_remote] = sum(this->elapsed);
	@targ[args[1]->ii_target] = sum(this->elapsed);
	start[arg1] = 0;
}

dtrace:::END
{
	printf("iSCSI read/write distributions (us):\n");
	printa(@rw);

	printf("\niSCSI read/write by client (total us):\n");
	normalize(@host, 1000);
	printa(@host);

	printf("\niSCSI read/write top %d targets (total us):\n", TOP_TARGETS);
	normalize(@targ, 1000);
	trunc(@targ, TOP_TARGETS);
	printa(@targ);
}
