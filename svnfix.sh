#!/bin/sh

DIR=${1:-.}

for i in dwt hd ini css htm php txt py xml conf ; do
    find $DIR -name "*.$i" -type f -print0 | xargs -0 flip -u
    find $DIR -name "*.$i" -type f -print0 | xargs -0 expand-in-place
    find $DIR -name "*.$i" -type f -print0 | xargs -0 svn propset svn:eol-style native
done

for i in ftl js java groovy ; do
    find $DIR -name "*.$i" -type f -print0 | xargs -0 flip -u
    find $DIR -name "*.$i" -type f -print0 | xargs -0 expand-in-place -t3
    find $DIR -name "*.$i" -type f -print0 | xargs -0 svn propset svn:eol-style native
done

for i in bat sh exe ; do
    find $DIR -name "*.$i" -type f -print0 | xargs -0 svn propset svn:executable
done

find $DIR -name "*.jpg" -type f -print0 | xargs -0 svn propset svn:mime-type image/jpeg
find $DIR -name "*.gif" -type f -print0 | xargs -0 svn propset svn:mime-type image/gif
find $DIR -name "*.png" -type f -print0 | xargs -0 svn propset svn:mime-type image/png
