#!/usr/bin/perl

while (<ARGV>)
{
    if (/(action|href|src)="([^"?#]+\/)?([^\/?"#]+)\??/) {
      print $3, "\n";
    }
}
