from django.test import SimpleTestCase
from finances.domain.services.format_sse import format_payload, format_sse


class SSEServiceTests(SimpleTestCase):
    def test_format_payload_serializes_json_with_prefix(self):
        data = {"key": "value"}
        lines = ["existing line"]
        
        result = format_payload(data, lines)
        
        self.assertEqual(result[0], "existing line")
        self.assertEqual(result[1], 'data: {"key": "value"}')
        self.assertEqual(result[2], "")
        self.assertEqual(result[3], "")

    def test_format_sse_includes_headers_and_payload(self):
        data = {"count": 1}
        event = "test_event"
        event_id = "123"
        
        result = format_sse(data, event, event_id)
        
        expected = (
            "event: test_event\n"
            "id: 123\n"
            'data: {"count": 1}\n'
            "\n"
            ""
        )
        self.assertEqual(result, expected)
