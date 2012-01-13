#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN { trace("Tracing...Output afer 10 seconds, or Ctrl-C\n"); }

io:::start
{
	start[args[0]->b_edev, args[0]->b_blkno] = timestamp;
}

io:::done
/start[args[0]->b_edev, args[0]->b_blkno]/
{
	this->elapsed =
	    (timestamp - start[args[0]->b_edev, args[0]->b_blkno]) / 1000000;
	@iot[args[1]->dev_statname,
	    args[0]->b_flags & B_READ ? "READS(ms)" : "WRITES(ms)"] =
	    quantize(this->elapsed);
	start[args[0]->b_edev, args[0]->b_blkno] = 0;
}
tick-10sec
{
	printa(@iot);
	exit(0);
}
