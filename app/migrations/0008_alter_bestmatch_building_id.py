# Generated by Django 3.2.20 on 2024-12-15 12:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0007_alter_bestmatch_entry_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bestmatch',
            name='building_id',
            field=models.BigIntegerField(blank=True, db_column='Building_ID', null=True),
        ),
    ]