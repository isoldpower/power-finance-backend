from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("data_write_core", "0015_webhook_secret_grace"),
    ]

    operations = [
        migrations.AddField(
            model_name="outboxentrymodel",
            name="traceparent",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="outboxentrymodel",
            name="tracestate",
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
        migrations.AddField(
            model_name="outboxentrymodel",
            name="baggage",
            field=models.CharField(blank=True, max_length=1024, null=True),
        ),
    ]
