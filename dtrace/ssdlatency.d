#!/usr/sbin/dtrace -s

fbt:ssd:ssdstrategy:entry
{
	start[arg0] = timestamp;
}

fbt:ssd:ssd_buf_iodone:entry
/start[arg2]/
{
	@time["ssd I/O latency (ns)"] = quantize(timestamp - start[arg2]);
	start[arg2] = 0;
}
