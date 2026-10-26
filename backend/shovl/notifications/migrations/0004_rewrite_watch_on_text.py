"""
The announcement that scheduled scans have started is stored with the feature's name in its
title and summary ("shovl watch is on for ...", later "shovll watch ..."). On 26 Oct 2026 the
product became xikomu and the feature murindzi, so those already in someone's bell would keep
showing the old names; this rewrites them. Only the watch_on kind carries the name; the other
kinds are left alone.

Going back leaves the text as it is: the old names are retired.
"""
from django.db import migrations

# Longest first, so "shovll watch" isn't half-replaced by "shovl watch".
OLD_NAMES = ("shovll watch", "xikomu watch", "shovl watch")
NEW_NAME = "murindzi"
TITLE_MAX = 200


def rewrite(text):
    for old in OLD_NAMES:
        text = text.replace(old, NEW_NAME)
    return text


def forwards(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")
    rows = Notification.objects.filter(kind="watch_on").only("id", "title", "summary")
    for item in rows.iterator():
        title = rewrite(item.title)
        if len(title) > TITLE_MAX:  # never longer than before today, but the column is 200
            title = title[:TITLE_MAX - 1] + "…"
        summary = rewrite(item.summary)
        if title != item.title or summary != item.summary:
            Notification.objects.filter(pk=item.pk).update(title=title, summary=summary)


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0003_rename_to_xikomu"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
