# Generated by Django 4.1.7 on 2024-02-11 10:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0027_collection_build_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collection',
            name='build_type',
            field=models.CharField(blank=True, choices=[('discrete', 'Discrete datasets'), ('conflated', 'Conflated datasets')], default='discrete', max_length=10, null=True),
        ),
    ]
