from datetime import datetime, timezone
from django.test import SimpleTestCase
from environment.domain.entities.user import UserEntity
from environment.application.dtos import ExternalUserInfo


class UserEntityTests(SimpleTestCase):
    def test_from_persistence_sets_fields_correctly(self):
        now = datetime.now(timezone.utc)
        user = UserEntity.from_persistence(
            id="user_123",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            last_login=now
        )
        
        self.assertEqual(user.id, "user_123")
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "Doe")
        self.assertEqual(user.last_login, now)

    def test_sync_with_external_updates_fields(self):
        old_now = datetime(2023, 1, 1, tzinfo=timezone.utc)
        new_now = datetime(2023, 10, 27, tzinfo=timezone.utc)
        user = UserEntity(
            id="user_123",
            email="old@example.com",
            first_name="Old",
            last_name="Name",
            last_login=old_now
        )
        
        external_info = ExternalUserInfo(
            external_user_id="user_123",
            email_address="new@example.com",
            first_name="New",
            last_name="User",
            last_login=new_now
        )
        
        user.sync_with_external(external_info)
        
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "User")
        self.assertEqual(user.last_login, new_now)
