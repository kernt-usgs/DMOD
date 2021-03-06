#!/usr/bin/env sh

INFO='Rebuild and update the local-source Python package at given path in the implied or specified Python virtual env'
SCRIPT_PARENT_DIR="$(cd "$(dirname "${0}")"; pwd)"

# Set SHARED_FUNCS_DIR (as needed by default_script_setup.sh) to the correct path before using it to source its contents
SHARED_FUNCS_DIR="${SCRIPT_PARENT_DIR}/shared"
if [ ! -d "${SHARED_FUNCS_DIR}" ]; then
    >&2 echo "Error: could not find shared script functions script at expected location:"
    >&2 echo "    ${SHARED_FUNCS_DIR}"
    exit 1
fi

# Import shared default script startup source
. ${SHARED_FUNCS_DIR}/default_script_setup.sh

# Import shared functions used for python-dev-related scripts
. ${SHARED_FUNCS_DIR}/py_dev_func.sh

usage()
{
    local _O="${NAME:?}:
${INFO:?}

Usage:
    ${NAME:?} -h|-help|--help
    ${NAME:?} [opts] <directory>

Options:
    --venv <dir>
        Set the directory of the virtual environment to use.
        By default, the following directories will be checked,
        with the first apparently valid virtual env being used:
        - ./venv/
        - ./.venv/
        - ${SCRIPT_PARENT_DIR:-?}/venv/
        - ${SCRIPT_PARENT_DIR:-?}/.venv/
"
    echo "${_O}" 2>&1
}

# Make sure we end up in the same starting directory, and deactivate venv if it was activated
cleanup_before_exit()
{
    # Make sure we don't accidentally run this more than once
    CLEANUP_DONE=$((${CLEANUP_DONE:=0}+1))
    if [ ${CLEANUP_DONE} -gt 1 ]; then
        >&2 echo "Warning: cleanup function being run for ${CLEANUP_DONE} time"
    fi
    # Go back to shell starting dir
    cd "${STARTING_DIR:?}"

    # If the flag is set that a virtual environment was activated, then deactivate it
    if [ ${VENV_WAS_ACTIVATED:-1} -eq 0 ]; then
        >&2 echo "Deactiving active virtual env at ${VIRTUAL_ENV}"
        deactivate
    fi
}

while [ ${#} -gt 0 ]; do
    case "${1}" in
        -h|--help|-help)
            usage
            exit
            ;;
        --venv)
            [ -n "${VENV_DIR:-}" ] && usage && exit 1
            VENV_DIR="$(py_dev_validate_venv_dir "${2}")"
            [ -z "${VENV_DIR:-}" ] && echo "Error: provided arg ${2} is not a valid virtual env directory" && exit 1
            shift
            ;;
        *)
            [ -n "${PACKAGE_DIR:-}" ] && usage && exit 1
            [ ! -d "${1}" ] && >&2 echo "Error: package directory arg is not an existing directory" && usage && exit 1
            PACKAGE_DIR="${1}"
            ;;
    esac
    shift
done

# Look for a default venv to use if needed
py_dev_detect_default_venv_directory

# Bail here if a valid venv is not set
[ -z "${VENV_DIR:-}" ] && echo "Error: no valid virtual env directory could be determined or was given" && exit 1

# Take appropriate action to activate the virtual environment if needed
py_dev_activate_venv

# Trap to make sure we "clean up" script activity before exiting
trap cleanup_before_exit 0 1 2 3 6 15

# Now, go into the package directory, build new dists, and install them
cd "${PACKAGE_DIR}"
PACKAGE_DIST_NAME="$(py_dev_extract_package_dist_name_from_setup)"
# Bail if we can't detect the appropriate package dist name
if [ -z "${PACKAGE_DIST_NAME}" ]; then
    >&2 echo "Error: unable to determine package dist name from ${PACKAGE_DIR}/setup.py"
    exit 1
fi

py_dev_clean_dist \
    && python setup.py sdist bdist_wheel \
    && pip uninstall -y ${PACKAGE_DIST_NAME:?} \
    && pip install --upgrade --find-links=./dist ${PACKAGE_DIST_NAME?} \
    && py_dev_clean_dist