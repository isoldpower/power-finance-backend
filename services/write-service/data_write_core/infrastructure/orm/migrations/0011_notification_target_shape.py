"""Bring notifications to the shape the API documents.

Three changes, one migration, because they describe one resource:

- `short` -> `title` and `message` -> `body` are RENAMES: the columns keep their
  data, only the names were wrong;
- `is_read` becomes `acknowledged_at`. A boolean and a timestamp are one field
  in this API — the same shape `deleted_at` uses — so the fact and its time
  cannot disagree. Rows already read are backfilled to the moment this migration
  runs rather than to `created_at`: we never recorded when the user saw them,
  and `created_at` would assert they were read the instant they were written,
  which is definitely false. The migration time is at least honestly "some point
  before now";
- `severity` and `subject_type` / `subject_id` arrive as explicit columns rather
  than living in `payload`. Both are filterable, and a JSON path in a WHERE
  clause is the kind of thing that is fine until it is the slow query.
"""

from django.db import migrations, models
from django.utils import timezone

DEFAULT_SEVERITY = "info"


def fill_acknowledged_at(apps, schema_editor):
    NotificationModel = apps.get_model("data_write_core", "NotificationModel")
    NotificationModel.objects.filter(is_read=True).update(acknowledged_at=timezone.now())


def fill_is_read(apps, schema_editor):
    NotificationModel = apps.get_model("data_write_core", "NotificationModel")
    NotificationModel.objects.update(is_read=False)
    NotificationModel.objects.filter(acknowledged_at__isnull=False).update(is_read=True)


class Migration(migrations.Migration):
    dependencies = [
        ("data_write_core", "0010_money_container_base"),
    ]

    operations = [
        migrations.RenameField(
            model_name="notificationmodel",
            old_name="short",
            new_name="title",
        ),
        migrations.RenameField(
            model_name="notificationmodel",
            old_name="message",
            new_name="body",
        ),
        migrations.AddField(
            model_name="notificationmodel",
            name="acknowledged_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(fill_acknowledged_at, fill_is_read),
        migrations.RemoveIndex(
            model_name="notificationmodel",
            name="notificatio_user_id_a4dd5c_idx",
        ),
        migrations.RemoveField(
            model_name="notificationmodel",
            name="is_read",
        ),
        migrations.AddField(
            model_name="notificationmodel",
            name="severity",
            field=models.CharField(default=DEFAULT_SEVERITY, max_length=16),
        ),
        migrations.AddField(
            model_name="notificationmodel",
            name="subject_type",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="notificationmodel",
            name="subject_id",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="notificationmodel",
            name="updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notificationmodel",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="notificationmodel",
            index=models.Index(
                fields=["user", "acknowledged_at"],
                name="notif_user_ack_idx",
            ),
        ),
    ]
