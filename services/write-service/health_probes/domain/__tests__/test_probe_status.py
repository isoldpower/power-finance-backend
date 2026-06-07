from django.test import SimpleTestCase

from health_probes.domain.entities import ProbeStatus


class ProbeStatusTests(SimpleTestCase):
    def test_ok_value_is_lowercase_string(self) -> None:
        self.assertEqual(ProbeStatus.OK.value, "ok")

    def test_degraded_value_is_lowercase_string(self) -> None:
        self.assertEqual(ProbeStatus.DEGRADED.value, "degraded")

    def test_probe_status_is_string_enum(self) -> None:
        self.assertIsInstance(ProbeStatus.OK, str)
        self.assertIsInstance(ProbeStatus.DEGRADED, str)

    def test_enum_has_only_two_members(self) -> None:
        self.assertEqual(len(list(ProbeStatus)), 2)
