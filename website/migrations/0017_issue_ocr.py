# Generated by Django 1.9.2 on 2016-11-25 02:29


from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0016_hunt_txn_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="issue",
            name="ocr",
            field=models.TextField(blank=True, default=b"", null=True),
        ),
    ]
