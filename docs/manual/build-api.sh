#!/usr/bin/env bash
set -e

projdir=$(dirname $0)
cd $projdir

# build API reference
quartodoc build

cd api-reference

# XXX: `sed -i` must be written as `sed -i'' -e` for portability:
# https://stackoverflow.com/questions/4247068/sed-command-with-i-option-failing-on-mac-but-works-on-linux

# fix
if [[ -f index.qmd.qmd ]]; then

    # HACK: fix generated file name
    mv index.qmd.qmd index.qmd

    # HACK: remove 'None' header and desc
    sed -i'' -e 's/^#*\s*None$//' index.qmd

    # HACK: add cross-reference to title
    sed -i'' -e 's/^# .*/\0 {#sec-api-ref}/' index.qmd
fi
