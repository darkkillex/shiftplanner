from django.db import migrations

GROUP = "Sola lettura"


def create_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name=GROUP)


def remove_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name=GROUP).delete()


class Migration(migrations.Migration):
    """Gruppo del profilo "Sola lettura" (vedi core/readonly.py)."""

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("reports", "0001_initial"),
    ]

    operations = [migrations.RunPython(create_group, remove_group)]
