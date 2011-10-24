#!/usr/bin/env perl

#use CGI;

#my $q = new CGI;
#my $commit = $q->param("commit");
my $commit = "b20cd8dbd051aa561257df965c0d3eaef5df069e";

print "Content-type:text/html\n\n";
print "<html>\n";
print "  <head>\n";
print "    <title>Git Mark Server</title>\n";
print "  </head>\n";
print "  <body>\n";
print "    <p>commit: $commit</p>\n";

$info = `zgrep ' $commit' /home/git/commit-map.txt.gz | awk '{print $1}'`;
$rev = `cd /home/git/emacs.bzr/trunk ; bzr revision-info $info | awk '{print $1}'`;

print "    <p>revision: $rev</p>\n";

print "  </body>\n";
print "</html>\n";
