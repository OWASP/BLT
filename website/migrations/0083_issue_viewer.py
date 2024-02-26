# Generated by Django 4.2.8 on 2024-02-02 17:52

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("website", "0082_requestaccess"),
    ]

    operations = [
        migrations.AddField(
            model_name="issue",
            name="viewer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="viewer",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
