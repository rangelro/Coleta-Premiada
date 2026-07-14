# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0004_merge_20260711_1216'),
        ('program', '0005_imovel_cidade_fk'),
        ('accounts', '0003_add_sobrenome_cadastro_completo'),
    ]

    operations = [
        migrations.AddField(
            model_name='registrocoleta',
            name='foto_url',
            field=models.CharField(
                blank=True, default='', max_length=500,
                help_text='Caminho relativo do objeto no MinIO (ex: evidencias/uuid.jpg). O frontend monta a URL do proxy a partir deste path.',
            ),
        ),
        migrations.DeleteModel(
            name='Evidencia',
        ),
    ]
