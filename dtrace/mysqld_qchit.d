#!/usr/sbin/dtrace -s

#pragma D option quiet

dtrace:::BEGIN
{
	printf("Tracing... Hit Ctrl-C to end.\n");
	hits = 0; misses = 0;
}

mysql*:::query-cache-hit,
mysql*:::query-cache-miss
{
	this->query = copyinstr(arg0);
}

mysql*:::query-cache-hit,
mysql*:::query-cache-miss
/strlen(this->query) > 60/
{
	this->query[57] = '.';
	this->query[58] = '.';
	this->query[59] = '.';
	this->query[60] = 0;
}

mysql*:::query-cache-hit
{
	@cache[this->query, "hit"] = count();
	hits++;
}

mysql*:::query-cache-miss
{
	@cache[this->query, "miss"] = count();
	misses++;
}

dtrace:::END
{
	printf("   %-60s %6s %6s\n", "QUERY", "RESULT", "COUNT");
	printa("   %-60s %6s %@6d\n", @cache);
	total = hits + misses;
	printf("\nHits     : %d\n", hits);
	printf("Misses   : %d\n", misses);
	printf("Hit Rate : %d%%\n", total ? (hits * 100) / total : 0);
}
