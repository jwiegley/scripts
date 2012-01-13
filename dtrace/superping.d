#!/usr/sbin/dtrace -s

#pragma D option quiet
#pragma D option switchrate=10hz

mib:::rawipOutDatagrams
/pid == $target/
{
	start = timestamp;
}

mib:::icmpInEchoReps
/start/
{
	this->delta = (timestamp - start) / 1000;
	printf("dtrace measured: %d us\n", this->delta);
	@a["\n  ICMP packet delta average (us):"] = avg(this->delta);
	@q["\n  ICMP packet delta distribution (us):"] =
	    lquantize(this->delta, 0, 1000000, 100);
	start = 0;
}
