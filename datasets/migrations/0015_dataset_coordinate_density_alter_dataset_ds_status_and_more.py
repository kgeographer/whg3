# Generated by Django 4.1.7 on 2024-05-23 18:57

import datasets.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('datasets', '0014_alter_dataset_volunteers'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='coordinate_density',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='dataset',
            name='ds_status',
            field=models.CharField(blank=True, choices=[('seed', 'Seed'), ('format_error', 'Invalid format'), ('format_ok', 'Valid format'), ('remote', 'Created remotely'), ('uploaded', 'File uploaded'), ('reconciling', 'Reconciling'), ('wd-complete', 'Wikidata recon completed'), ('accessioning', 'Accessioning'), ('indexed', 'Indexed')], max_length=12, null=True),
        ),
        migrations.AlterField(
            model_name='dataset',
            name='vis_parameters',
            field=models.JSONField(blank=True, default=datasets.models.default_vis_parameters, null=True),
        ),
    ]
