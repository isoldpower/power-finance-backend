from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("data_read_core", "0020_categories"),
    ]

    operations = [
        migrations.RemoveField(model_name="transactionreadmodel", name="category"),
        migrations.RemoveField(model_name="walletreadmodel", name="category"),
        migrations.RenameField(
            model_name="transactionreadmodel",
            old_name="category_reference",
            new_name="category",
        ),
        migrations.RenameField(
            model_name="walletreadmodel",
            old_name="category_reference",
            new_name="category",
        ),
    ]
