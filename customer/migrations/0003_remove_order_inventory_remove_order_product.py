# Generated by Django 5.1 on 2024-08-26 04:18

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('customer', '0002_order_inventory_order_product'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='inventory',
        ),
        migrations.RemoveField(
            model_name='order',
            name='product',
        ),
    ]