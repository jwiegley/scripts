#!/usr/sbin/dtrace -Cs

#pragma D option quiet
#pragma D option switchrate=10hz

typedef struct dns_name {
	unsigned int			magic;
	unsigned char *			ndata;
	/* truncated */
} dns_name_t;

pid$target::getname:entry
{
	self->arg0 = arg0;
}

pid$target::getname:return
/self->arg0/
{
	this->name = (dns_name_t *)copyin(self->arg0, sizeof (dns_name_t));
	printf("%s\n", copyinstr((uintptr_t)this->name->ndata));
	self->arg0 = 0;
}
