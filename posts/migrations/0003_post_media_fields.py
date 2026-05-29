from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("posts", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="heading",
            field=models.CharField(max_length=300, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="post",
            name="media",
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="post",
            name="media_type",
            field=models.CharField(
                blank=True,
                choices=[("image", "Image"), ("video", "Video")],
                max_length=10,
                null=True,
            ),
        ),
    ]
