#!/usr/bin/env bash
# See ./README.md → "Regenerating"
set -euo pipefail

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROTO_DIR="${LIB_DIR}/protobufs"

# protoc finds plugins (protoc-gen-go) on PATH; `go install` drops them in
# GOBIN (or GOPATH/bin), which often isn't exported. Add it so the Go step
# works without the caller having to touch their shell profile.
if command -v go >/dev/null 2>&1; then
  GO_BIN="$(go env GOBIN)"
  [ -z "${GO_BIN}" ] && GO_BIN="$(go env GOPATH)/bin"
  export PATH="${GO_BIN}:${PATH}"
fi

PYTHON_PKG_DIR="${LIB_DIR}/generated/python/kafka_messages"
GO_OUT_DIR="${LIB_DIR}/generated/go"
JAVA_OUT_DIR="${LIB_DIR}/generated/java"

rm -rf "${PYTHON_PKG_DIR}"
mkdir -p "${PYTHON_PKG_DIR}"

uv run --group dev python -m grpc_tools.protoc \
    --proto_path="${PROTO_DIR}" \
    --python_out="${PYTHON_PKG_DIR}" \
    --pyi_out="${PYTHON_PKG_DIR}" \
    "${PROTO_DIR}"/*.proto

case "$(uname -s)" in
  Darwin*) SED_INPLACE=(-i '') ;;
  *)       SED_INPLACE=(-i)    ;;
esac
for f in "${PYTHON_PKG_DIR}"/*_pb2.py "${PYTHON_PKG_DIR}"/*_pb2.pyi; do
  [ -e "$f" ] || continue
  sed "${SED_INPLACE[@]}" -E 's/^import ([a-z_]+_pb2) as /from . import \1 as /' "$f"
done

uv run --group dev python "${LIB_DIR}/_gen_init.py" "${PYTHON_PKG_DIR}"

echo "Generated Python bindings in ${PYTHON_PKG_DIR}"

rm -rf "${GO_OUT_DIR}"
mkdir -p "${GO_OUT_DIR}"

protoc \
    --proto_path="${PROTO_DIR}" \
    --go_out="${LIB_DIR}" \
    --go_opt=module=github.com/power-finance/kafka-messages-proto \
    "${PROTO_DIR}"/*.proto

echo "Generated Go bindings in ${GO_OUT_DIR}"

rm -rf "${JAVA_OUT_DIR}"
mkdir -p "${JAVA_OUT_DIR}"

protoc \
    --proto_path="${PROTO_DIR}" \
    --java_out="${JAVA_OUT_DIR}" \
    "${PROTO_DIR}"/*.proto

echo "Generated Java bindings in ${JAVA_OUT_DIR}"
