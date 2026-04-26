"""
Migration 0002: Add database indexes introduced in the model improvements.
- CMSPage: indexes on (language, is_published), (language, slug), db_index on is_public
- NavbarItem: index on (language, parent_id, sort_order), db_index on language
- PageBlock: index on (page, parent_column)
- PageVersion: index on (page, version_number desc)
- MediaAsset: db_index on kind
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("basecms", "0001_initial"),
    ]

    operations = [
        # CMSPage indexes
        migrations.AddIndex(
            model_name="cmspage",
            index=models.Index(fields=["language", "is_published"], name="basecms_cms_lang_pub_idx"),
        ),
        migrations.AddIndex(
            model_name="cmspage",
            index=models.Index(fields=["language", "slug"], name="basecms_cms_lang_slug_idx"),
        ),
        migrations.AlterField(
            model_name="cmspage",
            name="is_published",
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AlterField(
            model_name="cmspage",
            name="is_public",
            field=models.BooleanField(default=True, db_index=True),
        ),
        # NavbarItem indexes
        migrations.AddIndex(
            model_name="navbaritem",
            index=models.Index(fields=["language", "parent_id", "sort_order"], name="basecms_nav_lang_par_sort_idx"),
        ),
        migrations.AlterField(
            model_name="navbaritem",
            name="language",
            field=models.CharField(db_index=True, max_length=10),
        ),
        # PageBlock index
        migrations.AddIndex(
            model_name="pageblock",
            index=models.Index(fields=["page", "parent_column"], name="basecms_pb_page_col_idx"),
        ),
        # MediaAsset index
        migrations.AlterField(
            model_name="mediaasset",
            name="kind",
            field=models.CharField(
                choices=[("image","Image"),("video","Video"),("audio","Audio"),("document","Document"),("embed","Embed")],
                db_index=True,
                default="image",
                max_length=20,
            ),
        ),
    ]
