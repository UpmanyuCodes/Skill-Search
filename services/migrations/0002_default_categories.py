from django.db import migrations
from django.utils.text import slugify


def add_categories(apps, schema_editor):
    from services.testdata import CATEGORIES

    Category = apps.get_model("services", "Category")
    for order, (name, icon, desc, *_rest) in enumerate(CATEGORIES):
        Category.objects.get_or_create(
            name=name, defaults={"slug": slugify(name), "icon": icon, "description": desc, "order": order}
        )


class Migration(migrations.Migration):
    dependencies = [("services", "0001_initial")]
    operations = [migrations.RunPython(add_categories, migrations.RunPython.noop)]
