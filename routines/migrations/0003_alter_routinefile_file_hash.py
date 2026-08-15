from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("routines", "0002_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="routinefile",
            name="file_hash",
            field=models.CharField(db_index=True, max_length=64),
        ),
    ]
