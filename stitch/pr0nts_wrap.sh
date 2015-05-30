#!/usr/bin/env bash

# with a shitload of ram...
pr0ntsr --no-enblend-lock --stp 75m --ignore-errors "$@"
if [ $? -ne 0 ] ; then
    echo 'pr0nts failed, aborting cleanup'
    exit 1
fi

mkdir raw
mv *.* raw

if [ $(ls single/ |wc -l) -eq 1 ] ; then
    echo "Single output image detected: renaming"
    mv single/* single/$(basename $PWD).jpg
fi

