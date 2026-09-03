# Contract tests

The conventions in `API_TARGET.md` are statements about **every** endpoint, and
the services that implement them are four codebases in two languages. These
tests hold the whole surface to them at once, which is what per-service suites
structurally cannot do.

    make test-contract        # or: uv run pytest contract_tests -q

Nothing here needs Postgres, Kafka, Redis or a running stack. The suite reads:

| source | what it is asked |
| --- | --- |
| the three OpenAPI documents | what is actually served, and in what shape |
| `API_TARGET.md` | what was specified, endpoint by endpoint |
| `API_DIFF.md` | which deviations have been explained to clients |
| `infrastructure/kong/kong.yml` | which service each path would reach |
| each service's `http_contract` | which error codes can be raised |
| each service's cursor codec | whether the four still agree byte for byte |

Read-only, and driven off generated documents rather than a list kept here — so
an endpoint added tomorrow is covered without this directory changing. That is
the whole point: an audit passes once, a test keeps passing.

## What each module asserts

| module | assertion |
| --- | --- |
| `test_target_surface.py` | every target endpoint is served **or** documented as a deviation, and every served endpoint is targeted **or** documented. Fails in both directions |
| `test_response_conventions.py` | the envelope, the page meta, the money grammar, the timestamp format and the error shape, on every operation of every service |
| `test_cursor_agreement.py` | all four cursor implementations mint the same token for the same position |
| `test_error_vocabulary.py` | no undocumented `error.code` or `details[].code`, and every documented code carries the status the target gives it |
| `test_gateway_routing.py` | every path is routed, authenticated, and reaches the service that owns the resource |
| `test_staleness_fallback.py` | the internal 507 never reaches a client |

## The remaining fallback holes

`test_staleness_fallback.py` keeps a list, `MISSING_FALLBACK`, of reads that can
answer 507 with no write-side counterpart to be rerouted to — which surfaces to
a client as a 404 for a resource that exists. Three are left: `GET /accounts`,
`GET /accounts/{id}` and `GET /metrics`. Each is listed with its reason.

The list cannot rot in either direction. A gated read that is NOT on it must
have a fallback route, and a read that IS on it must NOT have one — so closing a
hole means deleting its entry, and the deletion is what hands the path to the
coverage test. Adding a gated read with no fallback and no entry fails too.

See the staleness GAP note in `API_IMPLEMENTATION.md` for what closing each of
the three would take.

## Adding to it

A new convention belongs in `test_response_conventions.py`, written against
`schema_walk.py` so it applies to every endpoint rather than to the one that
prompted it. A new deviation belongs in `API_DIFF.md` — the surface tests read
it, so documenting the deviation is what makes them pass.
