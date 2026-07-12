from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('custom_audit', '0002_alter_auditlog_tabela_alter_auditlog_timestamp_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='auditlog',
            name='cidade',
            field=models.CharField(blank=True, db_index=True, max_length=100, null=True),
        ),
    ]
