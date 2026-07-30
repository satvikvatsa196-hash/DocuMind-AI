from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0003_document_chunk_count_document_embedding_model_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='task_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
