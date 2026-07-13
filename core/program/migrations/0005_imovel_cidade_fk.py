import django.db.models.deletion
from django.db import migrations, models


def set_cidade_default(apps, schema_editor):
    Imovel = apps.get_model('program', 'Imovel')
    Imovel.objects.update(cidade_id=7)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_add_sobrenome_cadastro_completo'),
        ('program', '0004_programa_cidade'),
    ]

    operations = [
        # 1. Remove the old CharField
        migrations.RemoveField(
            model_name='imovel',
            name='cidade',
        ),
        # 2. Add the FK as nullable so existing rows don't violate NOT NULL
        migrations.AddField(
            model_name='imovel',
            name='cidade',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='imoveis',
                to='accounts.cidade',
            ),
        ),
        # 3. Populate all existing rows with city id=7
        migrations.RunPython(set_cidade_default, migrations.RunPython.noop),
        # 4. Make the FK non-nullable
        migrations.AlterField(
            model_name='imovel',
            name='cidade',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='imoveis',
                to='accounts.cidade',
            ),
        ),
    ]
