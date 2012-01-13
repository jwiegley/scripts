#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing PID %d ... Hit Ctrl-C for report.\n", $target);
}

pid$target:libcrypto*:*crypt*:entry
{
	self->crypt_start[probefunc] = vtimestamp;
}

pid$target:libcrypto*:*crypt*:return
/self->crypt_start[probefunc]/
{
	this->oncpu = vtimestamp - self->crypt_start[probefunc];
	@cpu[probefunc, "CPU (ns):"] = quantize(this->oncpu);
	@totals["encryption (ns)"] = sum(this->oncpu);
	self->crypt_start[probefunc] = 0;
}

dtrace:::END
{
	printa(@cpu); printa(@totals);
}
