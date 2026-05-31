import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0006_post_department'),
        ('users', '0003_district'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='district',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='posts',
                to='users.district',
            ),
        ),
    ]
