# Generated by Django 5.1 on 2024-09-03 09:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0004_inventory_l_inventory_m_inventory_s_inventory_xl'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='inventory',
            name='L',
        ),
        migrations.RemoveField(
            model_name='inventory',
            name='M',
        ),
        migrations.RemoveField(
            model_name='inventory',
            name='S',
        ),
        migrations.RemoveField(
            model_name='inventory',
            name='XL',
        ),
    ]
