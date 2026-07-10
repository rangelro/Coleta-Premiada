from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('program', '0003_ciclo_alter_consolidacao_ciclo_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='programa',
            name='cidade',
            field=models.ForeignKey(
                blank=True,
                help_text='Cidade à qual este programa pertence.',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='programas',
                to='accounts.cidade',
            ),
        ),
    ]
