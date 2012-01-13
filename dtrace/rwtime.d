#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing... Hit Ctrl-C to end.\n");
}

io:::start
{
	start_time[arg0] = timestamp;
}

io:::done
/(args[0]->b_flags & B_READ) && (this->start = start_time[arg0])/
{
	this->delta = (timestamp - this->start) / 1000;
	@plots["read I/O, us"] = quantize(this->delta);
	@avgs["average read I/O, us"] = avg(this->delta);
	start_time[arg0] = 0;
}

io:::done
/!(args[0]->b_flags & B_READ) && (this->start = start_time[arg0])/
{
	this->delta = (timestamp - this->start) / 1000;
	@plots["write I/O, us"] = quantize(this->delta);
	@avgs["average write I/O, us"] = avg(this->delta);
	start_time[arg0] = 0;
}

dtrace:::END
{
	printa("   %s\n%@d\n", @plots);
	printa(@avgs);
}
