#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	trace("Tracing HTTP errors... Hit Ctrl-C for report.\n");
}

http*:::request-done
/args[1]->hri_respcode >= 400 && args[1]->hri_respcode < 600/
{
	@[args[0]->ci_remote, args[1]->hri_respcode,
	    args[1]->hri_method, args[1]->hri_uri] = count();
}

dtrace:::END
{
	printf("%8s  %-16s %-4s %-6s %s\n", "COUNT", "CLIENT", "CODE",
	    "METHOD", "URI");
	printa("%@8d  %-16s %-4d %-6s %s\n", @);
}
