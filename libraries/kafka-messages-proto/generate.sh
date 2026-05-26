#!/usr/bin/env bash
# Regenerate language bindings from protobufs/*.proto into generated/.
# The output is committed so consumers don't need protoc installed locally.
#
# Source of truth: protobufs/*.proto
# Generated output: generated/<language>/...   ← do not edit by hand
#
# Run from anywhere; the script resolves paths relative to itself.
set -euo pipefail

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROTO_DIR="${LIB_DIR}/protobufs"
PYTHON_PKG_DIR="${LIB_DIR}/generated/python/kafka_messages"

rm -rf "${PYTHON_PKG_DIR}"
mkdir -p "${PYTHON_PKG_DIR}"

# --pyi_out emits *_pb2.pyi stub files so mypy can see the message
# classes; protoc/_pb2.py builds them dynamically from descriptors, which
# is invisible to static analysis.
uv run --group dev python -m grpc_tools.protoc \
    --proto_path="${PROTO_DIR}" \
    --python_out="${PYTHON_PKG_DIR}" \
    --pyi_out="${PYTHON_PKG_DIR}" \
    "${PROTO_DIR}"/*.proto

# protoc emits absolute imports rooted at the proto path (e.g.
# `import wallet_pb2`), but our generated files live inside a package.
# Rewrite to relative imports so the package is self-contained.
case "$(uname -s)" in
  Darwin*) SED_INPLACE=(-i '') ;;
  *)       SED_INPLACE=(-i)    ;;
esac
for f in "${PYTHON_PKG_DIR}"/*_pb2.py "${PYTHON_PKG_DIR}"/*_pb2.pyi; do
  [ -e "$f" ] || continue
  sed "${SED_INPLACE[@]}" -E 's/^import ([a-z_]+_pb2) as /from . import \1 as /' "$f"
done

# Emit the package __init__.py with re-exports derived from the freshly
# generated *_pb2 modules. Keeps `from kafka_messages import Foo`
# working without any hand-maintained API surface.
uv run --group dev python "${LIB_DIR}/_gen_init.py" "${PYTHON_PKG_DIR}"

echo "Generated Python bindings in ${PYTHON_PKG_DIR}"
