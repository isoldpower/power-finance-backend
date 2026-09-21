"""Bring the notification projection to the shape the API documents.

The read side mirrors the write side's `0011`, with one difference: nothing here
needs a reversible data backfill of its own. `acknowledged_at` is restated by
the projection the moment the write side republishes, so rows already read are
backfilled to the migration time only so the badge count is not wrong in the
window before that happens.
"""

from django.db import migrations, models
from django.utils import timezone

DEFAULT_SEVERITY = "info"


def fill_acknowledged_at(apps, schema_editor):
    NotificationReadModel = apps.get_model("data_read_core", "NotificationReadModel")
    NotificationReadModel.objects.filter(is_read=True).update(acknowledged_at=timezone.now())


def fill_is_read(apps, schema_editor):
    NotificationReadModel = apps.get_model("data_read_core", "NotificationReadModel")
    NotificationReadModel.objects.update(is_read=False)
    NotificationReadModel.objects.filter(acknowledged_at__isnull=False).update(is_read=True)


class Migration(migrations.Migration):
    dependencies = [
        ("data_read_core", "0013_account_currency_and_keyset"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="notificationreadmodel",
            name="rn_user_keyset_idx",
        ),
        migrations.RemoveIndex(
            model_name="notificationreadmodel",
            name="rn_user_unread_idx",
        ),
        migrations.RenameField(
            model_name="notificationreadmodel",
            old_name="short",
            new_name="title",
        ),
        migrations.RenameField(
            model_name="notificationreadmodel",
            old_name="message",
            new_name="body",
        ),
        migrations.AddField(
            model_name="notificationreadmodel",
            name="acknowledged_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(fill_acknowledged_at, fill_is_read),
        migrations.RemoveField(
            model_name="notificationreadmodel",
            name="is_read",
        ),
        migrations.AddField(
            model_name="notificationreadmodel",
            name="severity",
            field=models.CharField(default=DEFAULT_SEVERITY, max_length=16),
        ),
        migrations.AddField(
            model_name="notificationreadmodel",
            name="subject_type",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="notificationreadmodel",
            name="subject_id",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="notificationreadmodel",
            name="updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notificationreadmodel",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="notificationreadmodel",
            index=models.Index(
                fields=["user_id", "-created_at", "-id"],
                include=("severity", "title", "acknowledged_at"),
                name="rn_user_keyset_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="notificationreadmodel",
            index=models.Index(
                fields=["user_id", "acknowledged_at"],
                name="rn_user_unread_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="notificationreadmodel",
            index=models.Index(
                fields=["user_id", "severity"],
                name="rn_user_severity_idx",
            ),
        ),
    ]
