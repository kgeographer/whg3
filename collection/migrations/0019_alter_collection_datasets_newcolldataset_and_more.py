# Generated by Django 4.1.7 on 2023-12-16 18:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('datasets', '0006_alter_dataset_ds_status'),
        ('collection', '0018_colldataset_alter_collection_datasets'),
    ]

    operations = [
        # migrations.AlterField(
        #     model_name='collection',
        #     name='datasets',
        #     field=models.ManyToManyField(blank=True, related_name='old_datasets', through='collection.CollDataset', to='datasets.dataset'),
        # ),
        migrations.CreateModel(
            name='NewCollDataset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('collection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='collection.collection')),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datasets.dataset')),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        # migrations.AddField(
        #     model_name='collection',
        #     name='new_datasets',
        #     field=models.ManyToManyField(blank=True, related_name='new_datasets', through='collection.NewCollDataset', to='datasets.dataset'),
        # ),
    ]
