# Generated manually — adds direcionamento and status fields to RelatorioLLM

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='relatoriollm',
            name='direcionamento',
            field=models.TextField(
                blank=True, default='',
                help_text='Instrução adicional do usuário para guiar o tom/foco da análise.',
            ),
        ),
        migrations.AddField(
            model_name='relatoriollm',
            name='status',
            field=models.CharField(
                choices=[
                    ('pendente', 'Pendente'),
                    ('processando', 'Processando'),
                    ('concluido', 'Concluído'),
                    ('erro', 'Erro'),
                ],
                default='pendente',
                max_length=15,
            ),
        ),
        migrations.AlterField(
            model_name='relatoriollm',
            name='relatorio',
            field=models.TextField(blank=True, default=''),
        ),
    ]
