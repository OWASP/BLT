# Generated by Django 3.0.8 on 2020-08-26 03:51

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0062_company_is_active"),
    ]

    operations = [
        migrations.AddField(
            model_name="hunt",
            name="prize_runner",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
        migrations.AddField(
            model_name="hunt",
            name="prize_second_runner",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
        migrations.AddField(
            model_name="hunt",
            name="prize_winner",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
    ]
