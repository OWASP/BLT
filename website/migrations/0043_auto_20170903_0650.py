# Generated by Django 1.11.3 on 2017-09-03 06:50


from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0042_userprofile_issue_saved"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="userprofile",
            name="issue_saved",
        ),
        migrations.AddField(
            model_name="userprofile",
            name="issue_saved",
            field=models.ManyToManyField(blank=True, related_name="saved", to="website.Issue"),
        ),
    ]
