# Generated by Django 1.9.2 on 2016-11-25 03:46


from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0017_issue_ocr"),
    ]

    operations = [
        migrations.AddField(
            model_name="domain",
            name="email_event",
            field=models.CharField(blank=True, default=b"", max_length=255, null=True),
        ),
    ]
