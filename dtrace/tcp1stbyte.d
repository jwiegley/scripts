#!/usr/sbin/dtrace -s

tcp:::connect-established
{
	start[args[1]->cs_cid] = timestamp;
}

tcp:::receive
/start[args[1]->cs_cid] && (args[2]->ip_plength - args[4]->tcp_offset) > 0/
{
	@latency["1st Byte Latency (ns)", args[2]->ip_saddr] =
	    quantize(timestamp - start[args[1]->cs_cid]);
	start[args[1]->cs_cid] = 0;
}
