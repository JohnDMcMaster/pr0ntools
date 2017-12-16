fn=
collect=mcmaster

ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
    -c|--collection)
        collect="$2"
        shift
        shift
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

usage() {
    echo "usage: img2doku.sh <filename>"
}

fn=${ARGS[0]}
if [ -z "$fn" ] ; then
    usage
    exit 1
fi
fnbase=$(basename $fn)

vendor=$(echo $fn |cut -d_ -f 1)
chipid=$(echo $fn |cut -d_ -f 2)
dwbase=":${collect}:${vendor}:${chipid}"
flavor=$(echo $fnbase |sed 's/[a-zA-Z0-9\-]*_[a-zA-Z0-9\-]*_\(.*\).jpg/\1/')
desc="MZ @ 20x"
urlbase="https://siliconpr0n.org/map/$vendor/$chipid"

identify=$(identify $fn)
wh=$(echo $identify |cut -d\  -f3)
size=$(echo $identify |cut -d\  -f7)

echo "https://siliconpr0n.org/archive/doku.php?id=$collect:$vendor:$chipid"
echo

cat <<EOF
{{tag>collection_${collect} vendor_${vendor} type_unknown year_unknown foundry_unknown}}

====== Package ======

{{${dwbase}:pack_top.jpg?300|}}

<code>
</code>

{{${dwbase}:pack_btm.jpg?300|}}

<code>
</code>

====== Die ======

<code>
</code>

[[${urlbase}/$flavor/|$desc]]

    * [[${urlbase}/single/$fn|Single]] (${wh}, ${size})

EOF

