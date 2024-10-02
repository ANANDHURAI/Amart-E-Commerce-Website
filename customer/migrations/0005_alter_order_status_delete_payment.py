# Generated by Django 5.1 on 2024-09-15 18:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customer', '0004_payment'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('pending', 'pending'), ('confirmed', 'confirmed'), ('shipped', 'shipped'), ('delivered', 'delivered')], default='pending', max_length=20),
        ),
        migrations.DeleteModel(
            name='Payment',
        ),
    ]