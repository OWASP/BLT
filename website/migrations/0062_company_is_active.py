# Generated by Django 3.0.8 on 2020-08-22 09:21

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0061_payment"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="is_active",
            field=models.BooleanField(default=False),
        ),
    ]
