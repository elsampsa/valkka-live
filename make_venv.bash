#!/bin/bash
rm -r -f venv
# virtualenv --no-site-packages -p python3 venv
virtualenv --system-site-packages -p python3 venv
echo
echo "> Do this"
echo "cd venv"
echo "source bin/activate"
echo "export PYTHONPATH="
echo "> To test the packet, use"
echo "pip3 install ../dist/skeleton-0.1.0.tar.gz"
echo "> To exit, type"
echo "deactivate"
echo "cd .."
echo
