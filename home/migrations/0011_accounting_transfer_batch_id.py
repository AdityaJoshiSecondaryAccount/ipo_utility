from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0010_accounting_deleted_at_accounting_is_deleted_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="accounting",
            name="transfer_batch_id",
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),
    ]
