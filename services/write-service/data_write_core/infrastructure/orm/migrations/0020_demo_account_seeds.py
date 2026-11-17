import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('data_write_core', '0019_category_columns_swap'),
    ]

    operations = [
        migrations.CreateModel(
            name='DemoAccountSeedModel',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='demo_account_seed', serialize=False, to=settings.AUTH_USER_MODEL)),
                ('completed_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                'db_table': 'demo_account_seeds',
            },
        ),
    ]
