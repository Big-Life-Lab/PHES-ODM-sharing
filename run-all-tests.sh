#!/bin/sh
dir=$(dirname $0)

echo "unit tests"
$dir/run-unit-tests.sh

echo ""
echo "integration tests"
cd $dir/tests
python -m unittest int_test*.py
