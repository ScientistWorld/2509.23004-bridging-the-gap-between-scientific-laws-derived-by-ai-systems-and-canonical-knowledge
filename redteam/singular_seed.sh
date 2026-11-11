#!/bin/bash
set -euo pipefail
exec Singular --random="${AUDIT_SINGULAR_SEED:-11}" "$@"
