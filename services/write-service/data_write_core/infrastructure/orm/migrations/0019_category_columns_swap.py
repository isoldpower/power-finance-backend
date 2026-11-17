from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("data_write_core", "0018_category_foreign_keys"),
    ]

    operations = [
        migrations.RemoveField(model_name="transactionmodel", name="category"),
        migrations.RemoveField(model_name="walletmodel", name="category"),
        migrations.RenameField(
            model_name="transactionmodel",
            old_name="category_reference",
            new_name="category",
        ),
        migrations.RenameField(
            model_name="walletmodel",
            old_name="category_reference",
            new_name="category",
        ),
    ]
