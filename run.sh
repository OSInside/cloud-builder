#!/bin/bash
# Simple wrapper to run SUSE's build tool for packaging
# in a predefined chroot. The chroot is expected to be
# created by kiwi and suitable to build the package
#
set -e

# Options
ARGUMENT_LIST=(
    "root:"
    "package:"
)

if ! opts=$(getopt \
    --longoptions "$(printf "%s," "${ARGUMENT_LIST[@]}")" \
    --name "$(basename "$0")" \
    --options "" \
    -- "$@"
); then
    echo "run"
    echo "  --root <path>"
    echo "      Path to worker root dir"
    echo "  --package <path>"
    echo "      Path to package spec dir"
    exit 1
fi

eval set --"${opts}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --root)
            argRoot=$2
            shift 2
            ;;

        --package)
            argPackage=$2
            shift 2
            ;;

        *)
            break
            ;;
    esac
done

# Sanity
if [ ! "${UID}" = 0 ];then
    echo "You need to be root to do this"
    exit 1
fi
if [ ! "${argRoot}" ] || [ ! "${argPackage}" ];then
    echo "Specify --root and --package"
    exit 1
fi

# Functions
function finish {
    echo "Cleanup"
    chroot ${argRoot} umount /proc /dev &>/dev/null
    exit 0
}

trap finish EXIT

rsync -av "${argPackage}/" "${argRoot}/build"

chroot ${argRoot} mount -t proc proc /proc
chroot ${argRoot} mount -t devtmpfs devtmpfs /dev

chroot ${argRoot} bash -c "pushd /build && build --no-init --root /"
