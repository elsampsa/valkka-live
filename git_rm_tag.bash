#!/bin/bash

VERSION_MAJOR=0
VERSION_MINOR=2
VERSION_PATCH=1

ver=$VERSION_MAJOR=0
# ver2=$VERSION_MAJOR=0

echo $ver

git push --delete origin $ver
git tag -d $ver

# # list tags:
# git ls-remote --tags origin
# git tag
