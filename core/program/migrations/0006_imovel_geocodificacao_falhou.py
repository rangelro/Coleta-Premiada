from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0005_imovel_latitude_imovel_longitude'),
    ]

    operations = [
        migrations.AddField(
            model_name='imovel',
            name='geocodificacao_falhou',
            field=models.BooleanField(default=False),
        ),
    ]
