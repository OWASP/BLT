# Generated by Django 1.9.2 on 2016-11-25 20:05


from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0018_domain_email_event"),
    ]

    operations = [
        migrations.AddField(
            model_name="issue",
            name="status",
            field=models.CharField(blank=True, default=b"open", max_length=10, null=True),
        ),
    ]
