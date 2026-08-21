from rest_framework.response import Response

META_KEY = "idempotent_replay"


def mark_replay(response: Response, replayed: bool) -> Response:
    body = getattr(response, "data", None)
    if not isinstance(body, dict) or "error" in body:
        return response

    meta = body.get("meta")
    if not isinstance(meta, dict):
        meta = {}
        body["meta"] = meta

    meta[META_KEY] = replayed

    return response
