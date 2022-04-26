#!/bin/bash

function print_usage() {
  echo "Usage:"
  echo "    $0"
  echo "   --workplace                        Workplace where to apply formater"
  echo "   --fallback                         Fallback style format to be use: By default is Google"
  echo "   --apply                            <true|false> If true, format the code. Default is false"
  echo "   --help                             Print this page"
  echo
}

function log_() {
  echo "[$(basename "$0")] $*"
}

function parse_opts() {
  # Parse options
  local opt
  while [[ $# -gt 0 ]]; do
    opt="$1"

    case $opt in
    --workplace)
      workplace_path="$2"
      shift
      ;;
    -h | --help)
      print_usage
      exit 0
      ;;
    --fallback)
      fallback_style="${2}"
      shift
      ;;
    --apply)
      flag_apply="$2"
      shift
      ;;
    *)
      log_ "Unrecognized option '$opt'."
      exit 1
      ;;
    esac
    shift
  done
}

parse_opts ${@}

# If the path is not defined, default to the current
workplace_path="${workplace_path:-.}"

# If the fallback style is not defined, default to Google
fallback_style="${fallback_style:-Google}"

# If the apply flag is not set, default to false
flag_apply="${flag_apply:-false}"

log_ "workplace_path: ${workplace_path}"
log_ "fallback_style: ${fallback_style}"
log_ "flag apply format: ${flag_apply}"

/clang-format-wrapper.py --workplace ${workplace_path} --fallback "${fallback_style}" || exit_code=$?

exit ${exit_code}
