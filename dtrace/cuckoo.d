#!/usr/sbin/dtrace -s

#pragma D option quiet
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
	printf("%-20s %6s %6s %6s %s\n", "TIME", "PID", "PPID", "UID", "TEXT");
}

fbt::cnwrite:entry
{
	this->iov = args[1]->uio_iov;
	this->len = this->iov->iov_len;
	this->text = stringof((char *)copyin((uintptr_t)this->iov->iov_base,
	    this->len));
	this->text[this->len] = '\0';

	printf("%-20Y %6d %6d %6d %s\n", walltimestamp, pid, ppid, uid,
	    this->text);
}
