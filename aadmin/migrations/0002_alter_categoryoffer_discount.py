# Generated by Django 5.1 on 2024-08-26 14:45

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aadmin', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='categoryoffer',
            name='discount',
            field=models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(99)]),
        ),
    ]