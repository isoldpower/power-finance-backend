from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase
from django.db.models import Q
from uuid import uuid4

from finances.application.use_cases import (
    ListFilteredWebhooksQueryHandler, 
    ListFilteredWebhooksQuery
)
from finances.domain.entities import ResolvedFilterTree

class TestListFilteredWebhooksQueryHandler(SimpleTestCase):
    def setUp(self):
        self.repo = MagicMock()
        
        # Patch registry to avoid DB hits during handler init
        self.registry_patcher = patch("finances.application.use_cases.queries.list_filtered_webhooks.get_repository_registry")
        self.mock_registry = self.registry_patcher.start()
        
        self.handler = ListFilteredWebhooksQueryHandler(webhooks_repository=self.repo)

    def tearDown(self):
        self.registry_patcher.stop()

    def test_handle_simple_filter(self):
        query = ListFilteredWebhooksQuery(
            user_id=1,
            filter_body={"field_name": "title", "operator": "icontains", "value": "test"}
        )
        
        self.handler.handle(query)
        
        # Verify repo call
        self.repo.list_webhooks_with_filters.assert_called_once()
        args, _ = self.repo.list_webhooks_with_filters.call_args
        filter_tree = args[0]
        user_id = args[1]
        
        self.assertEqual(user_id, 1)

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
        self.repo.list_webhooks_with_filters.assert_called_once()

    def test_reject_unknown_field(self):
        query = ListFilteredWebhooksQuery(
            user_id=1,
            filter_body={"field_name": "malicious", "operator": "eq", "value": "hacked"}
        )

        with self.assertRaises(Exception):
            self.handler.handle(query)

    def test_uuid_field_policy(self):
        uuid_val = str(uuid4())
        query = ListFilteredWebhooksQuery(
            user_id=1,
            filter_body={"field_name": "id", "operator": "eq", "value": uuid_val}
        )
        
        self.handler.handle(query)
        self.repo.list_webhooks_with_filters.assert_called_once()
