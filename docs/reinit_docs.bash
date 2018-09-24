#!/bin/bash
#
# A script for changing author and package name in this docs directory only (if you copied this directory someplace else, to use with another module, etc.)
#
if [ $# -ne 2 ]; then
  echo "Give a author name and package name inside quotation marks, i.e.: ./reinit_docs.bash 'Janne Jantunen' 'package_name'"
  exit
fi

author=$1
name=$2

fs="*"
for f in $fs
do
  find $f -exec sed -i -r "s/valkka_live/$name/g" {} \;
  find $f -exec sed -i -r "s/valkka_live/$name/g" {} \;
  find $f -exec sed -i -r "s/valkka_live/$name/g" {} \;
  find $f -exec sed -i -r "s/Sampsa Riikonen/$author/g" {} \;
done

mkdir _static
./clean.bash
