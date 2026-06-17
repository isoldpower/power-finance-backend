"""StandardResultsPagination — envelope shape and limits."""

from data_read_core.shared.rest_framework import StandardResultsPagination


def test_limits():
    pagination = StandardResultsPagination()
    assert pagination.default_limit == 20
    assert pagination.max_limit == 100


def test_paginated_response_wraps_data_and_meta():
    pagination = StandardResultsPagination()
    pagination.limit = 20
    pagination.offset = 40
    pagination.count = 137

    response = pagination.get_paginated_response([{"id": "w1"}])

    assert response.data == {
        "data": [{"id": "w1"}],
        "meta": {"limit": 20, "offset": 40, "total": 137},
    }


def test_paginated_response_schema_requires_data_and_meta():
    schema = StandardResultsPagination().get_paginated_response_schema({"type": "array"})

    assert schema["required"] == ["data", "meta"]
    assert schema["properties"]["data"] == {"type": "array"}
    assert schema["properties"]["meta"]["required"] == ["limit", "offset", "total"]
