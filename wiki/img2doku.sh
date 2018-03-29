#!/usr/bin/env bash

#set e

collect=$COLLECT
if [ -z "$collect" ] ; then
    collect=mcmaster
fi

map=$MAP
if [ -z "$map" ] ; then
    map=1
fi

pack=1
link=1
nspre=
mappre=map

usage() {
    echo "usage: img2doku.sh <filename>"
    echo "--mappre      map URL prefix"
    echo "--nspre       wiki namespace prefix"
    echo "-m|--map      image as map"
    echo "-p|--page     image as page"
    echo "-P            no package image"
    echo "-L            no link text"
}

ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
    -c|--collection)
        collect="$2"
        shift
        shift
        ;;
    --mappre)
        mappre=$2
        shift
        shift
        ;;
    -m|--map)
        map=1
        shift
        ;;
    --nspre)
        nspre=$2
        shift
        shift
        ;;
    -p|--page)
        map=0
        shift
        ;;
    -P)
        pack=0
        shift
        ;;
    -L)
        link=0
        shift
        ;;
    -h|--help)
        usage
        exit 0
        ;;
    -*)
        usage
        exit 1
        ;;
    *)
        ARGS+=("$1")
        shift
        ;;
    esac
done

NA=${#ARGS[@]}
if [ "$NA" = 0 ] ; then
    usage
    exit 1
#elif [ "$NA" = 1 ] ; then
fi


links () {
    if [ "$link" = 1 ] ; then
        echo "https://siliconpr0n.org/archive/doku.php?id=${nspre}${collect}:$vendor:$chipid"
        echo "https://siliconpr0n.org/archive/doku.php?id=${nspre}${collect}:$vendor:$chipid:s"
        echo
        echo
    fi
}

header_pack() {
    cat <<EOF
{{tag>collection_${collect} vendor_${vendor} type_unknown year_unknown foundry_unknown}}

====== Package ======

EOF

    if [ "$pack" = 1 ] ; then
        cat <<EOF
{{${dwbase}:pack_top.jpg?300|}}

<code>
</code>

{{${dwbase}:pack_btm.jpg?300|}}

<code>
</code>
EOF
    else
        echo "Unknown"
    fi

    cat <<EOF

====== Die ======

<code>
</code>

EOF
}

if [ "$map" = 1 ] ; then
    fn=${ARGS[0]}
    fnbase=$(basename $fn)

    vendor=$(echo $fnbase |cut -d_ -f 1)
    chipid=$(echo $fnbase |cut -d_ -f 2)
    dwbase=":${nspre}${collect}:${vendor}:${chipid}"
    urlbase="https://siliconpr0n.org/${mappre}/$vendor/$chipid"

    links
    header_pack

    for fn in "${ARGS[@]}"; do
        fnbase=$(basename $fn)
        flavor=$(echo $fnbase |sed 's/[a-zA-Z0-9\-]*_[a-zA-Z0-9\-]*_\(.*\).jpg/\1/')
        identify=$(identify $fn)
        wh=$(echo $identify |cut -d\  -f3)
        size=$(echo $identify |cut -d\  -f7)
        cat <<EOF
[[${urlbase}/$flavor/|$flavor]]

    * [[${urlbase}/single/$fnbase|Single]] (${wh}, ${size})

EOF
    done
else
    fn=${ARGS[0]}
    fnbase=$(basename $fn)

    vendor=$(echo $fnbase |cut -d_ -f 1)
    chipid=$(echo $fnbase |cut -d_ -f 2)
    dwbase=":${nspre}${collect}:${vendor}:${chipid}"

    links
    header_pack

    for fn in "${ARGS[@]}"; do
        echo "{{${dwbase}:$fn?300|}}"
    done
fi

