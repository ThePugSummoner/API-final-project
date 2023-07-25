# Generated by Django 4.2.3 on 2023-07-20 19:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('LittleLemonAPI', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cart',
            name='price',
        ),
        migrations.AlterField(
            model_name='cart',
            name='unit_price',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='item_price', to='LittleLemonAPI.cart'),
        ),
    ]
