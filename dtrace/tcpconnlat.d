#!/usr/sbin/dtrace -s

tcp:::connect-request
{
	start[args[1]->cs_cid] = timestamp;
}

tcp:::connect-established
/start[args[1]->cs_cid]/
{
	@latency["Connect Latency (ns)", args[2]->ip_daddr] =
	    quantize(timestamp - start[args[1]->cs_cid]);
	start[args[1]->cs_cid] = 0;
}
