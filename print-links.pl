#!/usr/bin/perl

while (<ARGV>)
{
    if (/([^()\\= <>\/.'"{}#]+\.(html|osl|pdf|js|jpg|jpeg|gif|tif))/i) {
      print $1, "\n";
    }
}
