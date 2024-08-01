#!/usr/bin/env bash
set -e

projdir=$(dirname $0)
cd $projdir

# build API reference
quartodoc build

builddir=$projdir/api-reference
cd $builddir

# fix
if [[ -f index.qmd.qmd ]]; then

    # HACK: fix generated file name
    mv index.qmd.qmd index.qmd

    # HACK: remove 'None' header and desc
    sed -i 's/^#*\s*None$//' index.qmd

    # HACK: add cross-reference to title
    sed -i 's/^# .*/\0 {#sec-api-ref}/' index.qmd
fi
