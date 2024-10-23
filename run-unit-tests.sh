#!/bin/sh
dir=$(dirname $0)
python -m unittest discover $dir/tests
