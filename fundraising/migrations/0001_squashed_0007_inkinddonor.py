# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-01-20 17:50
from __future__ import unicode_literals

import django.db.models.deletion
import django.utils.timezone
import sorl.thumbnail.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    replaces = [('fundraising', '0001_squashed_0037_auto_20150709_1619'), ('fundraising', '0002_donation_donor_not_null'), ('fundraising', '0003_payment_stripe_charge_id_unique'), ('fundraising', '0004_remove_campaign_fks'), ('fundraising', '0005_delete_campaign'), ('fundraising', '0006_djangohero_location'), ('fundraising', '0007_inkinddonor')]

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Campaign',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('slug', models.SlugField(max_length=100)),
                ('goal', models.DecimalField(decimal_places=2, max_digits=9)),
                ('template', models.CharField(default='fundraising/campaign_default.html', max_length=50)),
                ('stretch_goal', models.DecimalField(blank=True, decimal_places=2, max_digits=9, null=True)),
                ('stretch_goal_url', models.URLField(blank=True, null=True)),
                ('start_date', models.DateTimeField(blank=True, null=True)),
                ('end_date', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=False, help_text='Should donation form be enabled or not?')),
                ('is_public', models.BooleanField(default=False, help_text='Should campaign be visible at all?')),
            ],
        ),
        migrations.CreateModel(
            name='DjangoHero',
            fields=[
                ('id', models.CharField(max_length=12, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('modified', models.DateTimeField(default=django.utils.timezone.now)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('stripe_customer_id', models.CharField(blank=True, max_length=100)),
                ('logo', sorl.thumbnail.fields.ImageField(blank=True, upload_to='fundraising/logos/')),
                ('url', models.URLField(blank=True, verbose_name='URL')),
                ('name', models.CharField(blank=True, max_length=100)),
                ('hero_type', models.CharField(blank=True, choices=[('individual', 'Individual'), ('organization', 'Organization')], max_length=30)),
                ('is_visible', models.BooleanField(default=False, verbose_name='Agreed to displaying on the fundraising page?')),
                ('is_subscribed', models.BooleanField(default=False, verbose_name='Agreed to being contacted by DSF?')),
                ('approved', models.NullBooleanField(verbose_name='Name, URL, and Logo approved?')),
            ],
            options={
                'verbose_name': 'Django hero',
                'verbose_name_plural': 'Django heroes',
            },
        ),
        migrations.CreateModel(
            name='Donation',
            fields=[
                ('id', models.CharField(max_length=12, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('modified', models.DateTimeField(default=django.utils.timezone.now)),
                ('interval', models.CharField(blank=True, choices=[('monthly', 'Monthly donation'), ('quarterly', 'Quarterly donation'), ('yearly', 'Yearly donation'), ('onetime', 'One-time donation')], max_length=20)),
                ('subscription_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=9, null=True)),
                ('stripe_subscription_id', models.CharField(blank=True, max_length=100)),
                ('stripe_customer_id', models.CharField(blank=True, max_length=100)),
                ('receipt_email', models.EmailField(blank=True, max_length=254)),
                ('campaign', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='fundraising.Campaign')),
                ('donor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='fundraising.DjangoHero')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=9, null=True)),
                ('stripe_charge_id', models.CharField(max_length=100, unique=True)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('donation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='fundraising.Donation')),
            ],
        ),
        migrations.CreateModel(
            name='Testimonial',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('author', models.CharField(max_length=255)),
                ('body', models.TextField()),
                ('is_active', models.BooleanField(default=True)),
            ],
        ),
        migrations.AlterField(
            model_name='donation',
            name='donor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='fundraising.DjangoHero'),
        ),
        migrations.RemoveField(
            model_name='donation',
            name='campaign',
        ),
        migrations.DeleteModel(
            name='Campaign',
        ),
        migrations.AddField(
            model_name='djangohero',
            name='location',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.CreateModel(
            name='InKindDonor',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('logo', sorl.thumbnail.fields.ImageField(blank=True, upload_to='fundraising/logos/')),
                ('url', models.URLField(blank=True, verbose_name='URL')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
            ],
            options={
                'verbose_name': 'in-kind hero',
                'verbose_name_plural': 'in-kind heroes',
            },
        ),
    ]
