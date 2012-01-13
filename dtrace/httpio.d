#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	trace("Tracing HTTP... Hit Ctrl-C for report.\n");
}

http*:::request-done
{
	@["received bytes"] = quantize(args[1]->hri_bytesread);
	@["sent bytes"] = quantize(args[1]->hri_byteswritten);
}
