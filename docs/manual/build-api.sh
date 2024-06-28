#!/usr/bin/env bash
set -e
dir=$(dirname $0)

# build API reference
quartodoc build

# HACK: fix generated file name
# HACK: remove 'None' header and desc
cd $dir/reference/
if [[ -f index.qmd.qmd ]]; then
    mv index.qmd.qmd index.qmd
    sed -i -e 's/^#*\s*None$//' index.qmd
fi
