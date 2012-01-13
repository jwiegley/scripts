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
pid$target:libz*:inflate:entry,
pid$target:libz*:deflate:entry
{
	self->compress_start = vtimestamp;
}

pid$target:libz*:inflate:return,
pid$target:libz*:deflate:return
/self->compress_start/
{
	this->oncpu = vtimestamp - self->compress_start;
	@cpu[probefunc, "CPU (ns):"] = quantize(this->oncpu);
	@totals["compression (ns)"] = sum(this->oncpu);
	self->compress_start = 0;
}

dtrace:::END
{
	printa(@cpu); printa(@totals);
}
