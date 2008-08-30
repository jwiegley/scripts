#!/usr/bin/env python
#
# catalog.py, version 1.3
#   by John Wiegley <johnw@newartisans.com>
#
# Depends on: Python (>= 2.5.1)
#   Optional: p7zip, rar

# TODO
#
# - add support for storing MD5 checksums
# - add support for comparing a directory to a recorded volume 
# - Write "ext" basic query (for searching based on file extensions)
# - Exclude trashes, device files (/dev, /proc), and mount locations

# INSTALL
#
# To get this working on my MacBook Pro using the MacPorts system for
# installing free software, I had to install the following packages by using
# "port install ...":
#
#   python25
#   py25-bz2
#   py25-hashlib
#   py25-zlib
#   p7zip
#
# If you want to inspect .rar files, you'll need a copy of the "rar"
# command-line utility.  I use the one that comes with the application
# SimplyRAR.  You'll have to link to the "rar" utility in the application
# bundle to someplace along your PATH.

# QUICK USAGE GUIDE
#
# First, index your volume(s).  You can run this kind of command over and over
# again:
#
#   catalog -f /tmp/catalog.db index /Users --name "Home directories" \
#     --location "Local disk" --kind "Directory"
#
# The --name option is required, but the --location and --kind parameters are
# optional.  Although the --name will be reported back to you, their content
# has no special meaning.
#
# Once indexed, you can search for what you need:
#
#   catalog -f /tmp/catalog.db name 'foo*'
#   catalog -f /tmp/catalog.db path '/foo'
#
# Set the environment variable CATALOG_FILE if you get tired of passing the -f
# option.

# ABOUT
#
# This is a disk cataloguing program.  For those familiar with UNIX, it's
# similar to "locate": the main difference being that it allows you to query
# unmounted filesets -- such as files on CD, in a disk image, or in a ZIP
# archive or tarball.
#
# Some of its salient features:
#
# 1. It descends into compressed and uncompressed archives:
#    a. .zip and .jar
#    b. .tar, .tar.gz, .tgz, .tar.bz2, .tbz
#    d. .rar
#    c. .7z
#
# 2. On OS/X, it descends into disk images, provided that:
#    a. They do not ask for agreement to a software license, and
#    b. They are not encrypted (unless explicitly requested)
#
# 3. Disk images within disk images are also searched, and so on recursively,
#    as long as #2 holds true.
#
# 4. Archives within disk images are also searched, but not disk images within
#    archives, or archives within archives.
#
# 5. All data is kept in simple relational tables, allowing you to create
#    complex SQL queries yourself to find exactly what you're looking for.
#    The database schema is described below.
#

# DATABASE SCHEMA
#
# It's all in the data, isn't it?  This program is mostly about seeding an SQL
# database so you can later write queries to your heart's content.  But to do
# that, you'll need to fully understand how the data is stored and related:
# its schema.
#
# The first table is "volumes", which tracks all the volumes you've indexed.
# Each volume has an "id", which is of particular interest.  The other
# elements in this table are purely informative:
#
#   "name"        TEXT      The unique name you gave to the volume
#   "location"    TEXT      Where it resides, physically or digitally
#   "kind"        TEXT      A description of the kind of volume it is
#   "totalCount"  INT       The total number of entries in the volume
#   "totalSize"   BIGINT    The total uncompressed size of those entries
#
# The next, and largest table in the database is "entries", which is almost
# always what you'll be searching by joining the "entries" table with some of
# the other tables.  Each entry has a "volumeId" referring back to the volume
# it's stored in.  So, to query for all entries in your "My Book" volume,
# you'd use this:
#
#   SELECT e."id", e."volumePath" FROM "entries" as e, "volumes" as v
#    WHERE v."name" = "My Book" AND e."volumeId" = v."id"
#
# The "entries" table has the largest number of columns, not all of which will
# have values (many of them will be NULL if the entry lives in an archive, for
# example).  They are:
#
#   "id"             INT        The entry's id
#   "volumeId"       INT        The id of the volume it resides in
#   "directoryId"    INT        The id of its parent (directory) entry
#   "name"           TEXT       Its filename 
#   "baseName"       TEXT       Its basename (sans extension)
#   "extension"      TEXT       Its extension
#   "kind"           INT        Its type (see below)
#   "permissions"    INT        Its UNIX file permissions, from octal
#   "owner"          INT        The owner's user id
#   "group"          INT        The owner's group id
#   "created"        TIMESTAMP  When it was created
#   "dataModified"   TIMESTAMP  When its data was last modified
#   "attrsModified"  TIMESTAMP  When attributes/metadata were modified
#   "dataAccessed"   TIMESTAMP  When its data was last accessed
#   "volumePath"     TEXT       Its full path within the volume
#
# There are several kinds of entries, whose "kind" matches one of the
# following:
#
#   1    A directory
#   2    A plain old file
#   3    A symbolic link
#   4    An OS/X package, like an application directory
#   7    An archive or disk image file
#   10   A special system file (like a named pipe, socket, device, etc)
#
# Each kind of entry has one (or two) associated attribute records.
# Directories have a directory record, files have a file record, and archives
# have both (a file record referring to the archive itself, and a directory
# record referring to the contents within).
#
# The "fileAttrs" table records information about actual files (things you
# could move around with the 'cp' command, let's say). It's columns are:
#
#   "id"           INT       The unique id of this attribute record
#   "entryId"      INT       The id of the entry it describes
#   "linkGroupId"  INT       Id of the "link group" this entry belongs to
#   "size"         BIGINT    The size of the file
#   "checksum"     CHAR(32)  An MD5 checksum of the contents (if possible)
#   "encoding"     TEXT      The encoding of its contents (if applicable)
#
# The "dirAttrs" table records information about directories and archive
# contents:
#
#   "id"           INT       The unique id of this attribute record
#   "entryId"      INT       The id of the entry it describes
#   "thisCount"    INT       The count of its immediate children
#   "thisSize"     BIGINT    The total size of its immediate children
#   "totalCount"   INT       The count of all "descended" entries
#   "totalSize"    BIGINT    The total size of all "descendend" entries
#
# The "linkAttrs" table is just for symbolic links, and basically it records
# which entry the link points to:
#
#   "id"           INT       Id of the link attribute
#   "entryId"      INT       Entry id for the symbolic link itself
#   "targetId"     INT       Id of the entry it points to
#
# The "metadata" table is special, and allows an unlimited amount of typed
# metadata to be stored for an entry.  Both individual items, and even lists
# and trees of typed items, may be stored using this table.  It's structure
# is:
#
#   "id"           INT       Id of the metadata item
#   "entryId"      INT       Id of the entry it relates to
#   "metadataId"   INT       (Optional) Id of parent metadata record
#   "name"         TEXT      Name of this metadata item
#   "type"         INT       The type of the metadata (see below)
#   "textValue"    TEXT      The value of a text metadata item
#   "intValue"     INT       The value of an integer metadata item
#   "dateValue"    TIMESTAMP The value of a date/time metadata item
#   "blobValue"    BYTEA     The value of a generic metadata item
#
# The "type" column determines which of the data columns is used, or even if
# any of them are used. The possible type values are:
#
#   1  Text
#   2  Integer
#   3  Date/time
#   4  Generic (byte array data, not searchable)
#   5  List
#
# In the case of a list, none of the data fields are used. Rather, it means
# there are other metadata entries, all with the same "entryId", whose
# "metadataId" refers back to the parent list. If members of the list are also
# list items, the results can be a tree of arbitrary depth.  However, every
# member of the tree will have the same "entryId" set, and the same "name",
# making it possible to query the entry tree based on the entry or name,
# without regard to its structure.
#
# A WORD ON INDICES: Since most name-based searches are going to be partial
# (LIKE) or regular expressions (RLIKE), and since the indices can get HUGE, I
# haven't bothered to index the textual fields, such as filenames.  Yes, there
# will be times when you want to search for an exact filename, and having an
# index would make this very fast, but it doesn't happen often enough for me
# to justify the many megabytes of space such an index would require.  But if
# you prefer to have indices, feel free to create them after your database has
# been initialized:
#
#   ALTER TABLE "entries" ADD INDEX(name(250))

import sqlite3

conn = None

import datetime
import zipfile
import tarfile
import os
import re
import sys
import optparse

from subprocess import Popen, PIPE
from os.path import *
from stat import *

def createTables():
    c = conn.cursor()

    c.execute("""
    CREATE TABLE "volumes"
        ("id" INTEGER PRIMARY KEY,
         "name" TEXT,
         "location" TEXT,
         "kind" TEXT,
         "totalCount" INTEGER,
         "totalSize" INTEGER)""")

    c.execute("""
    CREATE TABLE "entries"
        ("id" INTEGER PRIMARY KEY,
         "volumeId" INTEGER,
         "directoryId" INTEGER,
         "name" TEXT,
         "baseName" TEXT,
         "extension" TEXT,
         "kind" INTEGER,
         "permissions" INTEGER,
         "owner" INTEGER,
         "group" INTEGER,
         "created" INTEGER,
         "dataModified" INTEGER,
         "attrsModified" INTEGER,
         "dataAccessed" INTEGER,
         "volumePath" TEXT)""")

    c.execute("""
    CREATE TABLE "linkGroups"
        ("id" INTEGER PRIMARY KEY)""")

    c.execute("""
    CREATE TABLE "fileAttrs"
        ("id" INTEGER PRIMARY KEY,
         "entryId" INTEGER,
         "linkGroupId" INTEGER,
         "size" INTEGER,
         "checksum" CHAR(32),
         "encoding" TEXT)""")

    c.execute("""
    CREATE TABLE "dirAttrs"
        ("id" INTEGER PRIMARY KEY,
         "entryId" INTEGER,
         "thisCount" INTEGER,
         "thisSize" INTEGER,
         "totalCount" INTEGER,
         "totalSize" INTEGER)""")

    c.execute("""
    CREATE TABLE "linkAttrs"
        ("id" INTEGER PRIMARY KEY,
         "entryId" INTEGER,
         "targetId" INTEGER)""")

    c.execute("""
    CREATE TABLE "metadata"
        ("id" INTEGER PRIMARY KEY,
         "entryId" INTEGER,
         "metadataId" INTEGER,
         "name" TEXT,
         "type" INTEGER,
         "textValue" TEXT,
         "intValue" INTEGER,
         "dateValue" INTEGER,
         "blobValue" BLOB)""")
        
    conn.commit()

def initDatabase():
    version = 0
    try:
        c = conn.cursor()
        c.execute("SELECT \"version\" FROM \"version\"")
        row = c.fetchone()
        version = row[0]
    except:
        c = conn.cursor()
        c.execute("CREATE TABLE \"version\"(\"version\" INTEGER)")
        c.execute("INSERT INTO \"version\" (\"version\") VALUES (0)")
        conn.commit()

    if version < 1:
        createTables()

    if version < 10:
        # Add indices for the tables
        c.execute("CREATE INDEX \"entries_volumeId_idx\" ON \"entries\"(\"volumeId\")")
        c.execute("CREATE INDEX \"entries_directoryId_idx\" ON \"entries\"(\"directoryId\")")
        c.execute("CREATE INDEX \"fileAttrs_entryId_idx\" ON \"fileAttrs\"(\"entryId\")")
        c.execute("CREATE INDEX \"fileAttrs_linkGroupId_idx\" ON \"fileAttrs\"(\"linkGroupId\")")
        c.execute("CREATE INDEX \"dirAttrs_entryId_idx\" ON \"dirAttrs\"(\"entryId\")")
        c.execute("CREATE INDEX \"linkAttrs_entryId_idx\" ON \"linkAttrs\"(\"entryId\")")
        c.execute("CREATE INDEX \"linkAttrs_targetId_idx\" ON \"linkAttrs\"(\"targetId\")")
        c.execute("CREATE INDEX \"metadata_entryId_idx\" ON \"metadata\"(\"entryId\")")
        c.execute("CREATE INDEX \"metadata_metadataId_idx\" ON \"metadata\"(\"metadataId\")")

    if version < 10:
        version = 10
        c = conn.cursor()
        c.execute("UPDATE \"version\" SET \"version\" = %d" % version)
        conn.commit()

########################################################################

class FileAttrs:
    entry     = None
    linkGroup = None
    size      = None
    checksum  = None
    encoding  = None
    def __init__(self): pass    # this makes pylint happy again

class DirAttrs:
    entry      = None
    thisCount  = 0
    thisSize   = 0
    totalCount = 0
    totalSize  = 0
    def __init__(self): pass

class ArchiveAttrs(FileAttrs):
    dirAttrs = None
    def __init__(self):
        FileAttrs.__init__(self)
        self.dirAttrs = DirAttrs()

class LinkAttrs:
    entry  = None
    target = None
    def __init__(self): pass

(DIRECTORY, PLAIN_FILE, SYMBOLIC_LINK,
 PACKAGE, PACKAGE_DIRECTORY, PACKAGE_FILE,
 ARCHIVE, ARCHIVE_DIRECTORY, ARCHIVE_FILE,
 SPECIAL_FILE) = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)

def isArchiveName(fileName):
    return re.search("(\\.(zip|jar|7z|tgz|tbz|rar|dmg)|\\.tar(\\.gz|\\.bz2)?)$",
                     fileName)

lastMessage = ""

class Entry:
    id            = -1
    parent        = None
    parentId      = -1
    volume        = None
    path          = None                # current absolute pathname
    volumePath    = None                # path strictly within the volume
    name          = None
    baseName      = None
    extension     = None
    kind          = PLAIN_FILE
    permissions   = None
    owner         = None
    group         = None
    created       = None
    dataModified  = None
    attrsModified = None
    dataAccessed  = None
    infoRead      = False
    attrs         = None

    def __init__(self, volume = None, parent = None, path = None,
                 volumePath = None, name = None):
        self.volume     = volume
        self.volumePath = volumePath
        self.path       = path
        self.parent     = parent
        self.name       = name

        if parent:
            self.parentId = parent.id
        else:
            self.parentId = -1

        if name is not None:
            if len(name) > 0 and name[0] == '.':
                (self.baseName, self.extension) = splitext(name[1:])
                self.baseName = '.' + self.baseName
            else:
                (self.baseName, self.extension) = splitext(name)

            if len(self.extension) > 0 and self.extension[0] == '.':
                self.extension = self.extension[1:]

    def getParent(self):
        if self.parent: return self.parent
        if self.parentId < 0: return None

        self.parent = Entry()
        self.parent.load(self.parentId)

        return self.parent

    def isPlainFile(self):
        return self.kind == PLAIN_FILE
    def isSymbolicLink(self):
        return self.kind == SYMBOLIC_LINK
    def isDirectory(self):
        return self.kind == DIRECTORY
    def isPackage(self):
        return self.kind == PACKAGE
    def isArchive(self):
        return self.kind == ARCHIVE
    def isSpecialFile(self):
        return self.kind == SPECIAL_FILE

    def getInfo(self):
        if self.infoRead:
            return

        if self.id < 0:
            self.readInfo()
            return

        if self.isDirectory() or self.isPackage():
            return
        elif self.isArchive():
            return
        elif not self.isSpecialFile():
            c = conn.cursor()
            c.execute("""
              SELECT "linkGroupId", "size", "checksum", "encoding"
                FROM "fileAttrs" WHERE "entryId" = ?""", (self.id,))
            result = c.fetchone()
            if result:
                self.attrs = FileAttrs()
                self.attrs.entry     = self
                self.attrs.linkGroup = None
                self.attrs.size      = result[1]
                self.attrs.checksum  = result[2]
                self.attrs.encoding  = result[3]
        else:
            return

    def readInfo(self):
        info = os.lstat(self.path)

        if S_ISDIR(info[ST_MODE]):
            self.kind = DIRECTORY
            #m = re.search("\\.(app|oo3|dtBase)")
            #if m:
            #    self.kind = PACKAGE
            self.attrs = DirAttrs()
        elif S_ISLNK(info[ST_MODE]):
            self.kind = SYMBOLIC_LINK
            self.attrs = LinkAttrs()
        elif S_ISREG(info[ST_MODE]):
            if isArchiveName(self.name):
                self.kind = ARCHIVE
                self.attrs = ArchiveAttrs()
            else:
                self.kind = PLAIN_FILE
                self.attrs = FileAttrs()

            self.attrs.size     = long(info[ST_SIZE])
            self.attrs.checksum = self.readChecksum(self.path)
        else:
            self.kind = SPECIAL_FILE

        self.permissions   = info[ST_MODE]
        self.owner         = info[ST_UID]
        self.group         = info[ST_GID]
        self.dataAccessed  = datetime.datetime.fromtimestamp(info[ST_ATIME])
        self.dataModified  = datetime.datetime.fromtimestamp(info[ST_MTIME])
        self.attrsModified = datetime.datetime.fromtimestamp(info[ST_CTIME])

        self.infoRead = True

    def readChecksum(self, path):
        if opts.readChecksums:
            import md5
            fd = open(path)
            csum = md5.new()
            csum.update(fd.read())
            fd.close()
            return csum.hexdigest()
        else:
            return None

    def getChecksum(self):
        if not self.infoRead: self.getInfo()
        # Some archive members do not have attributes
        if not self.attrs:
            return None
        if self.isDirectory() or self.isPackage():
            return None
        elif self.isArchive():
            return None
        elif not self.isSpecialFile():
            return self.attrs.checksum
        else:
            return None

    def getCount(self):
        assert self.infoRead
        # Some archive members do not have attributes
        if not self.attrs:
            return None
        if self.isDirectory() or self.isPackage():
            return self.attrs.totalCount
        elif self.isArchive():
            return self.attrs.dirAttrs.totalCount
        else:
            return 1

    def getSize(self):
        assert self.infoRead
        # Some archive members do not have attributes
        if not self.attrs:
            return None
        if self.isDirectory() or self.isPackage():
            return self.attrs.totalSize
        elif self.isArchive():
            return self.attrs.dirAttrs.totalSize
        elif not self.isSpecialFile():
            return self.attrs.size
        else:
            return 0

    def scanEntries(self):
        if not self.isDirectory() and not self.isPackage() and \
           not self.isArchive():
            return

        attrs = self.attrs
        if self.isArchive():
            attrs = attrs.dirAttrs

        attrs.thisCount  = 0
        attrs.thisSize   = 0
        attrs.totalCount = 0
        attrs.totalSize  = 0

        entryPath = ""

        try:
            global lastMessage

            for entryName in os.listdir(self.path):
                entryPath = join(self.path, entryName)

                if re.match("/(dev|Network|automount)/", entryPath) or \
                   re.search("/\\.Trashes$", entryPath):
                    continue

                entry = createEntry(self.volume, self, entryPath,
                                    join(self.volumePath, entryName),
                                    entryName)
                entry.readInfo()
                entry.store()

                if entry.isPlainFile():
                    attrs.thisCount += 1
                    attrs.thisSize  += entry.getSize()

                elif not entry.isSymbolicLink():
                    if entry.isArchive() and entry.getSize() > (5 * 1024 * 1024):
                        print "Scanning", entry.volumePath
                        lastMessage = ""
                    else:
                        parts = entry.volumePath.split("/")
                        if parts > 3:
                            parts = parts[0:3]
                        theMessage = apply(join, parts)
                        if theMessage != lastMessage:
                            print "Scanning", theMessage
                            lastMessage = theMessage

                    entry.scanEntries()

                    attrs.totalCount += entry.getCount()
                    attrs.totalSize  += entry.getSize()

        except Exception, msg:
            print "Failed to index %s:" % (entryPath or self.path), msg

        attrs.totalCount += attrs.thisCount
        attrs.totalSize  += attrs.thisSize

    def load(self, id):
        self.id = id

        c = conn.cursor()
        c.execute("""
          SELECT "volumeId", "directoryId", "name", "baseName", "extension",
                 "kind", "permissions", "owner", "group", "created",
                 "dataModified", "attrsModified", "dataAccessed",
                 "volumePath"
          FROM "entries" WHERE "id" = ?""", (self.id,))

        result = c.fetchone()
        if result:
            (volumeId, parentId, name, baseName, extension,
             kind, permissions, owner, group, created,
             dataModified, attrsModified, dataAccessed,
             volumePath) = result
            
            self.volumeId      = volumeId
            self.parent        = None
            self.parentId      = parentId
            self.name          = name
            self.baseName      = baseName
            self.extension     = extension
            self.kind          = kind
            self.permissions   = permissions
            self.owner         = owner
            self.group         = group
            self.created       = created
            self.dataModified  = dataModified
            self.attrsModified = attrsModified
            self.dataAccessed  = dataAccessed
            self.volumePath    = volumePath

    def store(self):
        if self.id == -1:
            c = conn.cursor()
            c.execute("""
              INSERT INTO "entries"
                ("volumeId", "directoryId", "name", "baseName", "extension",
                 "kind", "permissions", "owner", "group", "created",
                 "dataModified", "attrsModified", "dataAccessed",
                 "volumePath")
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      ?, ?, ?, ?)""",
                (self.volume.id, self.parentId, self.name, self.baseName,
                 self.extension, self.kind, self.permissions, self.owner,
                 self.group, self.created, self.dataModified, self.attrsModified,
                 self.dataAccessed, self.volumePath))
            self.id = c.lastrowid
            conn.commit()
        else:
            c = conn.cursor()
            c.execute("""
              UPDATE "entries" SET
                "volumeId"      = ?,
                "directoryId"   = ?,
                "name"          = ?,
                "baseName"      = ?,
                "extension"     = ?,
                "kind"          = ?,
                "permissions"   = ?,
                "owner"         = ?,
                "group"         = ?,
                "created"       = ?,
                "dataModified"  = ?,
                "attrsModified" = ?,
                "dataAccessed"  = ?,
                "volumePath"    = ?)
              WHERE "id" = ?""",
                (self.volume.id, self.parentId, self.name, self.baseName,
                 self.extension, self.kind, self.permissions, self.owner,
                 self.group, self.created, self.dataModified, self.attrsModified,
                 self.dataAccessed, self.volumePath, self.id))

            c.execute("DELETE FROM \"fileAttrs\" WHERE \"entryId\" = ?", (self.id,))
            c.execute("DELETE FROM \"linkAttrs\" WHERE \"entryId\" = ?", (self.id,))
            c.execute("DELETE FROM \"dirAttrs\" WHERE \"entryId\" = ?", (self.id,))
            conn.commit()

        if self.isPlainFile() or self.isArchive():
            c = conn.cursor()
            c.execute("""
              INSERT INTO "fileAttrs"
                ("entryId", "linkGroupId", "size", "checksum", "encoding")
              VALUES (?, ?, ?, ?, ?)""",
                (self.id, None, self.attrs.size, self.attrs.checksum,
                 self.attrs.encoding))
            conn.commit()
        elif self.isSymbolicLink():
            # jww (2007-02-24): What if the target hasn't been stored yet?
            if False:
                c = conn.cursor()
                c.execute("""
                  INSERT INTO "linkAttrs" ("entryId", "targetId")
                  VALUES (?, ?)""", (self.id, self.attrs.target.id))
                conn.commit()

        if self.isDirectory() or self.isPackage() or self.isArchive():
            attrs = self.attrs
            if self.isArchive():
                attrs = attrs.dirAttrs

            c = conn.cursor()
            c.execute("""
              INSERT INTO "dirAttrs"
                ("entryId", "thisCount", "thisSize", "totalCount", "totalSize")
              VALUES (?, ?, ?, ?, ?)""",
                (self.id, attrs.thisCount, attrs.thisSize, attrs.totalCount,
                 attrs.totalSize))
            conn.commit()

    def drop(self):
        # jww (2007-08-05): What about the link group?
        c = conn.cursor()
        c.execute("DELETE FROM \"fileAttrs\" WHERE \"entryId\" = ?", (self.id,))
        c.execute("DELETE FROM \"linkAttrs\" WHERE \"entryId\" = ?", (self.id,))
        c.execute("DELETE FROM \"dirAttrs\" WHERE \"entryId\" = ?", (self.id,))
        c.execute("DELETE FROM \"entries\" WHERE \"id\" = ?", (self.id,))
        conn.commit()
        self.id = -1

def createEntry(volume, parent, path, volumePath, name):
    args = (volume, parent, path, volumePath, name)

    ext  = splitext(name[1:])[1]
    if ext == ".zip" or ext == ".jar":
        return apply(ZipFileEntry, args)
    elif ext == ".7z":
        return apply(SevenZipFileEntry, args)
    elif ext == ".rar":
        return apply(RarFileEntry, args)
    elif ext == ".dmg":
        return apply(DiskImageEntry, args)
    elif re.search("(\\.tar(\\.gz|\\.bz2)?|\\.tgz|\\.tbz)$", name):
        return apply(TarFileEntry, args)
    else:
        return apply(Entry, args)
    

def findEntryByVolumePath(volume, volPath):
    c = conn.cursor()
    c.execute("""SELECT "id" FROM "entries"
                 WHERE "volumeId" = ? AND "volumePath" = ?""",
                 (volume.id, volPath))
    data = c.fetchone()
    if data:
        (id,) = data

        entry = Entry()
        entry.id     = id
        entry.volume = volume

        entry.load(entry.id)

        return entry

    return None

def processEntriesResult(c, reporter):
    entries = []

    data = c.fetchone()
    while data:
        (volId, volName, volLocation, volKind, id) = data

        vol = Volume(None, volName, volLocation, volKind)
        vol.id = volId

        entry = Entry()
        entry.id = id
        entry.volume = vol
        entries.append(entry)

        data = c.fetchone()

    for entry in entries:
        entry.load(entry.id)
        reporter(entry)

    return entries

def findEntriesByName(name, reporter):
    name = re.sub('\*', '%', name)
    containsPercent = re.search('%', name)
    c = conn.cursor()
    c.execute("""
      SELECT v."id", v."name", v."location", v."kind", e."id"
      FROM "volumes" as v, "entries" as e
      WHERE e."name" %s ? AND e."volumeId" = v."id" """ %
              (containsPercent and "LIKE" or "="), (name,))
    return processEntriesResult(c, reporter)

def findEntriesByPath(path, reporter):
    c = conn.cursor()
    c.execute("""
      SELECT v."id", v."name", v."location", v."kind", e."id"
      FROM "volumes" as v, "entries" as e
      WHERE e."volumePath" LIKE ? AND e."volumeId" = v."id" """, (path,))
    return processEntriesResult(c, reporter)

class ZipFileEntry(Entry):              # a .zip archive file
    def __init__(self, volume, parent, path, volumePath, name):
        Entry.__init__(self, volume, parent, path, volumePath, name)

    def readStoredInfo(self, entry, info):
        entry.kind  = PLAIN_FILE
        entry.attrs = FileAttrs()

        entry.attrs.size   = info.file_size
        entry.dataModified = apply(datetime.datetime, info.date_time)

        entry.infoRead = True
        self.infoRead = True

    def scanEntries(self):
        assert self.isArchive()

        attrs = self.attrs
        attrs = attrs.dirAttrs

        attrs.thisCount  = 0
        attrs.thisSize   = 0
        attrs.totalCount = 0
        attrs.totalSize  = 0

        thisZipFile = None

        try:
            thisZipFile = zipfile.ZipFile(self.path)

            for info in thisZipFile.infolist():
                entry = Entry(self.volume, self, join(self.path, info.filename),
                              join(self.volumePath, info.filename),
                              info.filename)
                self.readStoredInfo(entry, info)
                entry.store()

                attrs.thisCount += 1
                attrs.thisSize  += info.file_size
        except Exception, msg:
            print "Failed to index %s:" % self.path, msg

        if thisZipFile:
            thisZipFile.close()

        attrs.totalCount += attrs.thisCount
        attrs.totalSize  += attrs.thisSize

class SevenZipFileEntry(Entry):              # a .7z archive file
    def readStoredInfo(self, entry, line):
        entry.kind  = PLAIN_FILE
        entry.attrs = FileAttrs()

        entry.attrs.size   = long(line[26:38])
        entry.dataModified = datetime.datetime.strptime(line[0:19], "%Y-%m-%d %H:%M:%S")

        entry.infoRead = True
        self.infoRead = True

    def scanEntries(self):
        assert self.isArchive()

        attrs = self.attrs
        attrs = attrs.dirAttrs

        attrs.thisCount  = 0
        attrs.thisSize   = 0
        attrs.totalCount = 0
        attrs.totalSize  = 0

        pipe = None
        
        try:
            pipe = Popen("7za l \"%s\"" % self.path, shell = True,
                         stdout = PIPE).stdout

            for line in pipe.readlines():
                if not re.match("20", line):
                    continue

                filename = line[53:-1]

                entry = Entry(self.volume, self, join(self.path, filename),
                              join(self.volumePath, filename), filename)
                self.readStoredInfo(entry, line)
                entry.store()

                attrs.thisCount += 1
                attrs.thisSize  += entry.attrs.size
        except Exception, msg:
            print "Failed to index %s:" % self.path, msg

        if pipe:
            pipe.close()

        attrs.totalCount += attrs.thisCount
        attrs.totalSize  += attrs.thisSize

class RarFileEntry(Entry):              # a .rar archive file
    def scanEntries(self):
        assert self.isArchive()

        attrs = self.attrs
        attrs = attrs.dirAttrs

        attrs.thisCount  = 0
        attrs.thisSize   = 0
        attrs.totalCount = 0
        attrs.totalSize  = 0

        pipe = None
        insideListing = False

        try:
            pipe = Popen("rar lt \"%s\"" % self.path, shell = True,
                         stdout = PIPE).stdout

            lines = pipe.readlines()
            i = 0
            while i < len(lines):
                if not insideListing:
                    if re.match("-----", lines[i]):
                        insideListing = True
                else:
                    if re.match("-----", lines[i]):
                        insideListing = False
                        i += 1
                        continue

                    items = lines[i].strip().split()
                    i += 1

                    while len(items) > 10:
                        begin = items[0] + " " + items[1]
                        items = items[1:]
                        items[0] = begin

                    filename = items[0]

                    entry = Entry(self.volume, self, join(self.path, filename),
                                  join(self.volumePath, filename), filename)

                    entry.kind  = PLAIN_FILE
                    entry.attrs = FileAttrs()

                    entry.attrs.size   = long(items[1])
                    entry.dataModified = datetime.datetime.strptime(items[4] + " " + items[5],
                                                                    "%d-%m-%y %H:%M")

                    entry.infoRead = True
                    self.infoRead = True
                    entry.store()

                    attrs.thisCount += 1
                    attrs.thisSize  += entry.attrs.size

                i += 1
        except Exception, msg:
            print "Failed to index %s:" % self.path, msg

        if pipe:
            pipe.close()

        attrs.totalCount += attrs.thisCount
        attrs.totalSize  += attrs.thisSize

class TarFileEntry(Entry):              # an (un)compressed .tar archive file
    def readStoredInfo(self, entry, info):
        # jww (2007-03-26): Parse out symbolic links here
        entry.kind  = PLAIN_FILE
        entry.attrs = FileAttrs()

        entry.attrs.size   = info.size
        entry.permissions  = info.mode
        entry.owner        = info.uid
        entry.group        = info.gid
        entry.dataModified = datetime.datetime.fromtimestamp(info.mtime)

        entry.infoRead = True
        self.infoRead = True

    def scanEntries(self):
        assert self.isArchive()

        attrs = self.attrs
        attrs = attrs.dirAttrs

        attrs.thisCount  = 0
        attrs.thisSize   = 0
        attrs.totalCount = 0
        attrs.totalSize  = 0

        thisTarFile = None

        try:
            thisTarFile = tarfile.open(self.path)

            for info in thisTarFile.getmembers():
                entry = Entry(self.volume, self, join(self.path, info.name),
                              join(self.volumePath, info.name),
                              basename(info.name))
                self.readStoredInfo(entry, info)
                entry.store()

                attrs.thisCount += 1
                attrs.thisSize  += info.size
        except Exception, msg:
            print "Failed to index %s:" % self.path, msg

        if thisTarFile:
            thisTarFile.close()

        attrs.totalCount += attrs.thisCount
        attrs.totalSize  += attrs.thisSize

class DiskImageEntry(Entry):              # a .dmg file
    def scanEntries(self):
        assert self.isArchive()

        attrs = self.attrs
        attrs = attrs.dirAttrs

        attrs.thisCount  = 0
        attrs.thisSize   = 0
        attrs.totalCount = 0
        attrs.totalSize  = 0

        pipe = None
        path = None
        skip = False
        
        try:
            pipe = Popen("hdiutil imageinfo \"%s\"" % self.path,
                         shell = True, stdout = PIPE).stdout

            for line in pipe.readlines():
                if re.search("Software License Agreement: true", line) or \
                   (not opts.openEncryptedImages and re.search("Encrypted: true", line)):
                    skip = True
                    pipe.close()
                    return

            if not skip:
                pipe = Popen("hdiutil attach \"%s\" -readonly %s" %
                             (self.path, "-mountrandom /tmp -noverify -noautofsck"),
                             shell = True, stdout = PIPE).stdout

                for line in pipe.readlines():
                    match = re.search("(/tmp/.+)", line)
                    if match:
                        path = match.group(1)
                        break

        except Exception, msg:
            print "Failed to index %s:" % self.path, msg
            
        if pipe:
            pipe.close()

        try:
            if path:
                dirEntry = Entry(self.volume, self, path, self.volumePath, self.name)
                dirEntry.readInfo()
                dirEntry.id = self.id   # spoof id, to skip the "man in the middle"
                dirEntry.scanEntries()

                attrs.thisCount += dirEntry.getCount()
                attrs.thisSize  += dirEntry.getSize()

            attrs.totalCount += attrs.thisCount
            attrs.totalSize  += attrs.thisSize

        finally:
            p = Popen("hdiutil detach \"%s\"" % path, shell = True, stdout = PIPE)
            os.waitpid(p.pid, 0)

class Volume:
    id         = -1
    topEntry   = None
    name       = "unnamed"
    location   = "unknown location"
    kind       = "unknown kind"
    totalCount = 0
    totalSize  = 0

    def __init__(self, path, name, location, kind):
        self.path     = path and normpath(path)
        self.name     = name
        self.location = location
        self.kind     = kind

    def clearEntries(self):
        print "Clearing previous entries for volume %s" % self.name

        c = conn.cursor()
        c.execute("""SELECT "id" FROM "volumes" WHERE "name" = ?""", (self.name,))
        data = c.fetchone()
        assert data
        volumeId = data[0]

        c.execute("""SELECT "id" FROM "entries" WHERE "volumeId" = ?""", (volumeId,))
        data = c.fetchone()

        idsToDelete = []
        while data:
            idsToDelete.append(data[0])
            data = c.fetchone()
        
        c = conn.cursor()
        for entryId in idsToDelete:
            c.execute("DELETE FROM \"fileAttrs\" WHERE \"entryId\" = ?", (entryId,))
            c.execute("DELETE FROM \"linkAttrs\" WHERE \"entryId\" = ?", (entryId,))
            c.execute("DELETE FROM \"dirAttrs\" WHERE \"entryId\" = ?", (entryId,))

        c.execute("DELETE FROM \"entries\" WHERE \"volumeId\" = ?", (volumeId,))
        c.execute("DELETE FROM \"volumes\" WHERE \"id\" = ?", (volumeId,))
        conn.commit()

    def scanEntries(self):
        if self.id > 0:
            self.clearEntries()
            self.id = -1

        if self.id < 0:
            c = conn.cursor()
            c.execute("""
              INSERT INTO "volumes" ("name", "location", "kind", "totalCount", "totalSize")
              VALUES (?, ?, ?, 0, 0)""", (self.name, self.location, self.kind))
            self.id = c.lastrowid
            conn.commit()

        self.topEntry = Entry(self, None, self.path, "", "")
        self.topEntry.readInfo()

        if self.topEntry.isDirectory():
            self.topEntry.scanEntries()
            self.topEntry.store()
            self.totalCount = self.topEntry.attrs.totalCount
            self.totalSize  = self.topEntry.attrs.totalSize
        elif self.topEntry.isArchive():
            self.topEntry.scanEntries()
            self.topEntry.store()
            self.totalCount = self.topEntry.attrs.dirAttrs.totalCount
            self.totalSize  = self.topEntry.attrs.dirAttrs.totalSize
        else:
            print "Volume is neither a directory nor an archive"

        c.execute("""
          UPDATE "volumes" SET "totalCount" = ?, "totalSize" = ? WHERE "id" = ?""",
            (self.totalCount, self.totalSize, self.id))

        print "Volume", self.path, "total count is", self.totalCount
        print "Volume", self.path, "total size  is", self.totalSize

def findVolumeByName(name):
    c = conn.cursor()
    c.execute("""
      SELECT "id", "location", "kind", "totalCount", "totalSize"
      FROM "volumes" WHERE "name" = ?""", (name,))
    result = c.fetchone()
    if result:
        (id, location, kind, totalCount, totalSize) = result

        vol = Volume(None, name, location, kind)
        vol.id         = id
        vol.totalCount = totalCount
        vol.totalSize  = totalSize

        return vol

    return None

########################################################################

parser = optparse.OptionParser()

parser.add_option('-E', '--open-encrypted',
                  action='store_true', dest='openEncryptedImages', default=False,
                  help='descend into encrypted images (may ask for password)')
parser.add_option('-C', '--checksum',
                  action='store_true', dest='readChecksums', default=False,
                  help='calculate MD5 checksum of cataloged files (where possible)')
parser.add_option('-f', '--file', metavar='CATALOG_FILE',
                  type='string', action='store', dest='databaseName',
                  default=os.path.expanduser('~/.catalogdb'),
                  help='filename where the data will be stored')
parser.add_option('-k', '--kind',
                  type='string', action='store', dest='volumeKind',
                  help='kind of the volume being indexed')
parser.add_option('-l', '--location',
                  type='string', action='store', dest='volumeLocation',
                  help='location of the volume being indexed')
parser.add_option('-v', '--verbose',
                  action='store_true', dest='verbose', default=False,
                  help='report activity options.verbosely')

(opts, args) = parser.parse_args()

conn = sqlite3.connect(opts.databaseName)
if not conn:
    print "Could not connect to SQLite3 database '%s'" % opts.databaseName
    sys.exit(1)

try:
    cursor = conn.cursor()
    initDatabase()

    command = args[0]

    def print_result(entry):
        csum = entry.getChecksum()
        if csum:
            print entry.volume.name, "=> %s <%s>" % (entry.volumePath, csum)
        else:
            print entry.volume.name, "=>", entry.volumePath
        sys.stdout.flush()

    if command == "name":
        if len(args) == 1:
            print "usage: catalog name <LIKE PATTERN>"
            sys.exit(1)

        for name in args[1:]:
            findEntriesByName(name, print_result)

    elif command == "path":
        if len(args) == 1:
            print "usage: catalog path <LIKE PATTERN>"
            sys.exit(1)

        for path in args[1:]:
            findEntriesByPath(path, print_result)

    elif command == "index":
        if len(args) == 1:
            print "usage: catalog index <PATH> [NAME]"
            sys.exit(1)

        path = args[1]

        if len(args) == 2:
            name = basename(path)
        else:
            name = args[2]

        vol = findVolumeByName(name)
        if not vol:
            vol = Volume(path, name, opts.volumeLocation, opts.volumeKind)
        else:
            vol.path = normpath(path)

        vol.scanEntries()

finally:
    conn.close()
