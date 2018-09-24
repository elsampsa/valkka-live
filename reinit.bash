#!/bin/bash
name=$(basename $PWD)
if [ "$name" == "skeleton" ]
then
  echo will not overwrite default skeleton directory!
  exit
fi
echo initializing project $name
# rename python module directory
mv skeleton $name
# replace project names

fs="MANIFEST.in README.md setup.py $name/* docs/*"
for f in $fs
do
  find $f -exec sed -i -r "s/skeleton/$name/g" {} \;
  find $f -exec sed -i -r "s/Skeleton/$name/g" {} \;
  find $f -exec sed -i -r "s/your_package_name/$name/g" {} \;
done
# recompile documentation
cd docs
mkdir _static
./clean.bash
# ./compile.bash # we can compile documentation only after this module is on the pythonpath!
cd ..
# decouple from git
rm -rf .git .gitignore

