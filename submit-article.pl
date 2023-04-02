#!/usr/bin/perl

use File::Temp qw(tempfile);

my ($tmp_fh, $tempfile) = tempfile();
my $site = shift @ARGV;
my $dest = shift @ARGV;
my $file = shift @ARGV;
my $printed_metadata = 0;
my @tags = ();
my $created;
my $slug = "";

open (FILE, $file);
while (<FILE>) {
    if (/:CREATED: +\[([-0-9]+) .+\]/) {
        $created = $1;
    }
    elsif (/:SLUG: +([-a-z0-9]+)/) {
        $slug = $1;
        # print "found slug $slug\n";
    }

    next if /^:PROPERTIES:/ .. /^:END:/;

    if (/^#\+/ && $printed_metadata == 0) {
        print $tmp_fh "---\n";
        $printed_metadata = 1;
    }
    elsif (/^$/ && $printed_metadata == 1) {
        print $tmp_fh "---\n";
        $printed_metadata = 2;
    }

    if (/^#\+filetags: :(.+): *$/) {
        @tags = split ':', $1;
        my @tagscopy = grep { $_ !~ /^publish/ } @tags;
        my $tagstr = join ", ", @tagscopy;
        print $tmp_fh "tags: $tagstr\n";
    }
    elsif (/^#\+title: (.+)$/) {
        if ($slug eq "") {
            $slug = lc $1;
            $slug =~ s/[^a-z0-9 ]//g;
            $slug =~ s/ /-/g;
        }

        s/^#\+//;
        print $tmp_fh $_;
    }
    elsif ($printed_metadata < 2) {
        s/^#\+//;
        print $tmp_fh $_;
    }
    else {
        print $tmp_fh $_;
    }
}
close FILE;

close $tmp_fh;

my $target = "${created}-${slug}.org";

# print "tags = ", (join ', ', @tags), "\n";
# print "slug = $slug\n";

if (grep(/^publish=${site}$/, @tags)) {
    rename $tempfile => $target;
    print "published $target\n";
}
