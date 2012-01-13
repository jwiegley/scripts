#!/usr/sbin/dtrace -s

io:::start
{
	start[arg0] = timestamp;
}

io:::done
/start[arg0]/
{
	@time["disk I/O latency (ns)"] = quantize(timestamp - start[arg0]);
	start[arg0] = 0;
}
