#!/bin/bash
name=$(basename $PWD)
if [ $# -ne 1 ]; then
  echo "Give a author name inside quotation marks"
  exit
fi

echo "Setting author to "$1
echo "Are you sure?"
read -n1 -r -p "Press q to quit, space to continue..." key

if [ "$key" = '' ]; then
  echo "running sed"
  fs="MANIFEST.in README.md setup.py $name/* docs/*"
  for f in $fs
  do
    find $f -exec sed -i -r "s/Sampsa Riikonen/$1/g" {} \;
  done
  
else
  echo
  echo "cancelled"
fi

