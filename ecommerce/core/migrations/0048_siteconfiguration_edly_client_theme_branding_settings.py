# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2020-03-16 08:09
from __future__ import unicode_literals

from django.db import migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0047_businessclient_enterprise_customer_uuid'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteconfiguration',
            name='edly_client_theme_branding_settings',
            field=jsonfield.fields.JSONField(default={}, help_text='JSON string containing edly client theme branding settings.', verbose_name='Edly client theme branding settings'),
        ),
    ]
