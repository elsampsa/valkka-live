#!/bin/bash
# sphinx-apidoc -f -e -o . ..
sphinx-autogen *.rst
#./fix_rst.py
#cd generated
#sphinx-autogen *.rst
#cd ..
make html

# # ** Gitlab users **
# # Enable these lines if you want to hack gitlab for online docs
# # here we assume that you keep your gitlab wiki repositories in $HOME/gitlab_wikis
# wiki=$HOME/gitlab_wikis/valkka_live
# rsync -v -r _build $wiki/

# # ** Gitlab users **
# # When you create your gitlab wiki for the first time, run also this:
# cd $wiki
# git add $(git ls-files -o --exclude-standard)
# git commit -a -m "initial commit"
# git push
