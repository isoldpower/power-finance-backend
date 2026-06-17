# kafka-messages-proto

Protobuf schemas and generated language bindings for cross-service Kafka events.

- **Source of truth:** `protobufs/*.proto`.
- **Generated output:** `generated/<language>/...` — committed so consumers don't
  need `protoc` installed locally. Do not edit by hand.

## Regenerating

Run `./generate.sh` (resolves paths relative to itself, runnable from anywhere).
It regenerates both Python and Go bindings:

- **Python** — `--pyi_out` emits `*_pb2.pyi` stubs so mypy can see message
  classes (the `_pb2.py` modules build them dynamically from descriptors, which
  is invisible to static analysis). protoc emits absolute imports rooted at the
  proto path, so the script rewrites them to relative imports to keep the package
  self-contained, then regenerates `__init__.py` re-exports so
  `from kafka_messages import Foo` works without a hand-maintained surface.
- **Go** — `--go_opt=module=<module path>` strips that prefix from each file's
  `go_package`, landing files at `generated/go/events/v1/*.pb.go`. Requires
  `protoc-gen-go` on `PATH`.

## Packaging

The importable Python package is the generated output: the wheel/editable install
maps `generated/python/kafka_messages` → `kafka_messages` (see `pyproject.toml`).
