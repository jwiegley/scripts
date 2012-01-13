#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	LINES = 20; line = 0;
}

profile:::tick-1sec
/--line <= 0/
{
	printf("  UDP:    %12s %12s %12s %12s %12s\n", "out(bytes)",
	    "outErrors", "in(bytes)", "inErrors", "noPort");
	line = LINES;
}

mib:::udp*InDatagrams   { @in = sum(arg0);      }
mib:::udp*OutDatagrams  { @out = sum(arg0);     }
mib:::udpInErrors       { @inErr = sum(arg0);   }
mib:::udpInCksumErrs    { @inErr = sum(arg0);   }
mib:::udpOutErrors      { @outErr = sum(arg0);  }
mib:::udpNoPorts        { @noPort = sum(arg0);  }

profile:::tick-1sec
{
	printa("          %@12d %@12d %@12d %@12d %@12d\n",
	    @out, @outErr, @in, @inErr, @noPort);
	clear(@out); clear(@outErr); clear(@in); clear(@inErr); clear(@noPort);
}
