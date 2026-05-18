#!/usr/bin/env bash
# Regenerate Python bindings from proto/*.proto into kafka_messages_proto/_generated/.
# The output is committed: consumers don't need protoc installed locally.
#
# Run from anywhere; the script resolves paths relative to itself.
set -euo pipefail

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROTO_DIR="${LIB_DIR}/proto"
OUT_DIR="${LIB_DIR}/kafka_messages_proto/_generated"

rm -rf "${OUT_DIR}"
mkdir -p "${OUT_DIR}"
touch "${OUT_DIR}/__init__.py"

# --pyi_out emits *_pb2.pyi stub files so mypy can see the message
# classes; protoc/_pb2.py builds them dynamically from descriptors, which
# is invisible to static analysis.
uv run --group dev python -m grpc_tools.protoc \
    --proto_path="${PROTO_DIR}" \
    --python_out="${OUT_DIR}" \
    --pyi_out="${OUT_DIR}" \
    "${PROTO_DIR}"/*.proto

# protoc emits absolute imports rooted at the proto path (e.g.
# `import wallet_pb2`), but our generated files live inside a package.
# Rewrite to relative imports so the package is self-contained.
case "$(uname -s)" in
  Darwin*) SED_INPLACE=(-i '') ;;
  *)       SED_INPLACE=(-i)    ;;
esac
for f in "${OUT_DIR}"/*_pb2.py "${OUT_DIR}"/*_pb2.pyi; do
  [ -e "$f" ] || continue
  sed "${SED_INPLACE[@]}" -E 's/^import ([a-z_]+_pb2) as /from . import \1 as /' "$f"
done

echo "Generated bindings in ${OUT_DIR}"
