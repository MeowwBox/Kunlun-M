import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("index", "0009_projectvendors_source"),
    ]

    operations = [
        migrations.AlterField(
            model_name="scantask",
            name="is_finished",
            field=models.IntegerField(default=3),
        ),
        migrations.AddField(
            model_name="scantask",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name="scantask",
            name="started_at",
            field=models.DateTimeField(default=None, null=True),
        ),
        migrations.AddField(
            model_name="scantask",
            name="finished_at",
            field=models.DateTimeField(default=None, null=True),
        ),
        migrations.AddField(
            model_name="scantask",
            name="exit_code",
            field=models.IntegerField(default=None, null=True),
        ),
        migrations.AddField(
            model_name="scantask",
            name="error_message",
            field=models.TextField(default=None, null=True),
        ),
        migrations.AddField(
            model_name="scantask",
            name="source_type",
            field=models.CharField(default=None, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name="scantask",
            name="source_archive",
            field=models.CharField(default=None, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="scantask",
            name="source_dir",
            field=models.CharField(default=None, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="scantask",
            name="options_json",
            field=models.TextField(default=None, null=True),
        ),
    ]
