#!/usr/bin/env ruby -w
# -*- coding: utf-8 -*-
#
# Filename: contacts2bbdb.rb
# Description: Converts addresses from OSX Addressbook.app to BBDB format
# Author: Anupam Sengupta (anupamsg ... A-T ... G - M - A - I - L )
# Maintainer: Anupam Sengupta
#
# (c) 2007-2016 Anupam Sengupta.
#
# Created: Fri May 25 15:53:22 2007
# Version: 1.0
# Last-Updated:
# By: Anupam Sengupta
# Update #: 733
# URL: http://slashusr.wordpress.com
# Keywords: `BBDB', 'OSX', 'contacts', 'convert'
# Compatibility: GNU Emacs 21 and above
#
#--------------------------------------------------------------------
#
# Commentary:
#
# Converts the addresses and contacts from Apple OSX's system addressbook
# format (Addressbook.app) to Emacs' BBDB format.
#
# Requires the following additional software:
#
# 1. Ruby V1.8 and above (http://www.ruby-lang.org/)
# 2. Big Brother Database (BBDB) package for Emacs (http://bbdb.sourceforge.net/)
# 3. The 'contacts' program to read Addressbook's contacts
# (http://gnufoo.org/contacts/)
#
# Usage:
#
# 1. Install Ruby, BBDB and contacts, if not already present
# 2. Backup the OSX Address book (export the addresses as addressbook archive)
# 3. Run this Ruby script to generate the converted records in BBDB format in the STDOUT
# 4. Save the STDOUT output of this script to bbdb.new
#
# $ ruby contacts2bbdb.rb > bbdb.new
#
# 5. Replace your .bbdb file with bbdb.new
#
#--------------------------------------------------------------------
#
# Change log:
#
#
#--------------------------------------------------------------------
#
# License: GNU GPL V2.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING. If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street, Fifth
# Floor, Boston, MA 02110-1301, USA.
#--------------------------------------------------------------------
#
Delim = "\t" # Default delimiter
ContactsProg = '/usr/bin/env contacts' # The contacts program
#
ContactsProgParams = '-H -l'
#
# A map between the LDIF field names and the actual field name
ContactFields = {
  :fn => 'firstName',
  :ln => 'lastName',
  :c => 'company',
  :nn => 'nickName',
  :he => 'homeEmail',
  :we => 'workEmail',
  :oe => 'otherEmail',
  :hp => 'Home',
  :mp => 'Mobile',
  :Mp => 'Main',
  :wp => 'Work',
}
#
ContactFormatOpts = ContactFields.keys # Options to pass to the contacts program
ContactsProgFormat = "'%" + ContactFormatOpts.inject { |s, f| s.to_s + "#{Delim}%#{f.to_s}" } + "'"
ContactsFullExec = "#{ContactsProg} #{ContactsProgParams} -f #{ContactsProgFormat}"
#
output = `#{ContactsFullExec}`.split(/\n/) # Read the output of contacts program
#
# Start parsing the contacts output
records = output.map do |line|
  record = Hash.new(nil)
  line.chomp.split(Delim).each_with_index { |f, i| record[ContactFields[ContactFormatOpts[i]]] = f.strip unless f =~ /^\s*$/ }
  record
end
#
# Start outputing the details to STDOUT
puts <<END
;; -*-coding: utf-8-emacs;-*-
;;; file-version: 6
END
#
for r in records do
  r['nickName'] = nil # No need for the nick names.
  outs = %w{ firstName lastName nickName company }.inject("[") { |s, f| s + (r[f] ? "\"#{r[f]}\" " : "nil ") }
  outs = %w{ Home Main Mobile Work}.inject(outs + "(") { |s, f| r[f] ? s + "[\"#{f}\" \"#{r[f].strip}\"] " : s } + ") "
  outs = %w{ homeEmail workEmail otherEmail }.inject(outs + " nil (") { |s, f| r[f] ? s + "\"#{r[f]}\" " : s } + ") "
  outs += "((creation-date . \"2009-02-08\") (timestamp . \"2009-02-08\")) nil]"
  puts outs
end
# End of contacts2bbdb.rb script
