# Generated by Django 4.1.7 on 2024-03-25 16:00

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0028_alter_collection_build_type'),
    ]

    operations = [
        migrations.RenameField(
            model_name='collection',
            old_name='created',
            new_name='create_date',
        ),
        migrations.AddField(
            model_name='colldataset',
            name='date_added',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='collection',
            name='version',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
