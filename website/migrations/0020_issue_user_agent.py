# Generated by Django 1.9.2 on 2016-11-25 21:45


from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0019_issue_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="issue",
            name="user_agent",
            field=models.CharField(blank=True, default=b"", max_length=255, null=True),
        ),
    ]
