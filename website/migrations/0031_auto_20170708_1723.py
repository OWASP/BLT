# Generated by Django 1.9.2 on 2017-07-08 21:23


from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0030_auto_20170708_1722"),
    ]

    operations = [
        migrations.AlterField(
            model_name="issue",
            name="closed_date",
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
    ]
