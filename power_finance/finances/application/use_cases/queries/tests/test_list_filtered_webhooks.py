from unittest.mock import MagicMock
from django.test import SimpleTestCase
from django.db.models import Q

from finances.application.use_cases import (
    ListFilteredWebhooksQueryHandler, 
    ListFilteredWebhooksQuery
)
from finances.domain.entities import ResolvedFilterTree

class TestListFilteredWebhooksQueryHandler(SimpleTestCase):
    def setUp(self):
        self.repo = MagicMock()
        self.handler = ListFilteredWebhooksQueryHandler(webhooks_repository=self.repo)

    def test_handle_simple_filter(self):
        query = ListFilteredWebhooksQuery(
            user_id=1,
            filter_body={"field_name": "title", "operator": "icontains", "value": "test"}
        )
        
        self.handler.handle(query)
        
        # Verify repo call
        self.repo.list_webhooks_with_filters.assert_called_once()
        args, _ = self.repo.list_webhooks_with_filters.call_args
        tree = args[0]
        user_id = args[1]
        
        self.assertIsInstance(tree, ResolvedFilterTree)
        self.assertEqual(user_id, 1)
        # Check Q object
        self.assertEqual(str(tree.query), str(Q(title__icontains="test")))

    def test_handle_complex_filter(self):
        query = ListFilteredWebhooksQuery(
            user_id=1,
            filter_body={
                "and": [
                    {"field_name": "is_active", "operator": "eq", "value": True},
                    {"field_name": "created_at", "operator": "gte", "value": "2023-01-01"}
                ]
            }
        )
        
        self.handler.handle(query)
        
        args, _ = self.repo.list_webhooks_with_filters.call_args
        tree = args[0]
        # Check Q object (Note: AND order might vary but string rep should be stable for simple ones)
        expected_q = Q(is_active=True) & Q(created_at__gte="2023-01-01")
        self.assertEqual(str(tree.query), str(expected_q))

    def test_reject_unknown_field(self):
        query = ListFilteredWebhooksQuery(
            user_id=1,
            filter_body={"field_name": "malicious", "operator": "eq", "value": "hacked"}
        )

        # Unknown/malicious fields should cause a parse/policy error, and the
        # handler should propagate that error without calling the repository.
        with self.assertRaises(Exception):
            self.handler.handle(query)
        self.repo.list_webhooks_with_filters.assert_not_called()

    def test_uuid_field_policy(self):
        uuid_val = "550e8400-e29b-41d4-a716-446655440000"
        query = ListFilteredWebhooksQuery(
            user_id=1,
            filter_body={"field_name": "id", "operator": "eq", "value": uuid_val}
        )
        
        self.handler.handle(query)
        
        args, _ = self.repo.list_webhooks_with_filters.call_args
        tree = args[0]
        # The Q object should contain the UUID string (or UUID object if converted)
        self.assertIn(uuid_val, str(tree.query))
