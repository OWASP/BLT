# Generated by Django 3.0.7 on 2020-06-19 05:51

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("website", "0052_auto_20200619_0540"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanyAdmin",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "role",
                    models.IntegerField(choices=[(0, "Super Admin"), (1, "Hunt Admin")], default=0),
                ),
                ("is_active", models.BooleanField(default=True)),
            ],
        ),
        migrations.RenameField(
            model_name="subscription",
            old_name="domains_per_month",
            new_name="number_of_domains",
        ),
        migrations.RemoveField(
            model_name="domain",
            name="admin",
        ),
        migrations.AddField(
            model_name="company",
            name="admin",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.DeleteModel(
            name="DomainAdmin",
        ),
        migrations.AddField(
            model_name="companyadmin",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="website.Company",
            ),
        ),
        migrations.AddField(
            model_name="companyadmin",
            name="domain",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="website.Domain",
            ),
        ),
        migrations.AddField(
            model_name="companyadmin",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
