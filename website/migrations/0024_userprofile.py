# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-02-03 14:44


import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def add_profiles(apps, schema_editor):
    UserProfile = apps.get_model('website', 'UserProfile')
    user_app, user_model = settings.AUTH_USER_MODEL.split('.')
    User = apps.get_model(user_app, user_model)
    for user in User.objects.all():
        UserProfile(user=user).save()


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('website', '0023_invitefriend'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_avatar', models.ImageField(blank=True, null=True, upload_to=b'avatars/')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='userprofile',
                                              to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(add_profiles, reverse_code=migrations.RunPython.noop),
    ]
