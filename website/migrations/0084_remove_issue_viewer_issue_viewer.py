# Generated by Django 4.2.8 on 2024-02-02 21:48

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("website", "0083_issue_viewer"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="issue",
            name="viewer",
        ),
        migrations.AddField(
            model_name="issue",
            name="viewer",
            field=models.ManyToManyField(
                blank=True,
                null=True,
                related_name="viewer",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]