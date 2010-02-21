#!/usr/bin/perl

while (<ARGV>)
{
    if (/(href|src)="([^"?#]+\/)?([^\/?"#]+)\??/) {
      print $3, "\n";
    }
}
