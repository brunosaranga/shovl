"""
Lowercases every stored email, so the case-insensitive unique rule in 0005 can be added.

If two accounts would end up with the same address, this stops and names them instead of
choosing one. Merge or delete the extra account by hand, then run migrate again. On Render
that fails the build, and the version already running stays up.
"""
from collections import defaultdict

from django.db import migrations


def lowercase_emails(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    db = schema_editor.connection.alias

    by_address = defaultdict(list)
    for pk, email in User.objects.using(db).values_list("pk", "email"):
        by_address[(email or "").strip().lower()].append((pk, email))

    clashes = {address: rows for address, rows in by_address.items() if len(rows) > 1}
    if clashes:
        details = "; ".join(
            f"{address}: " + ", ".join(f"id {pk} ({email})" for pk, email in rows)
            for address, rows in sorted(clashes.items())
        )
        raise RuntimeError(
            "Some accounts differ only in the case of their email, so they cannot all be kept: "
            f"{details}. Merge or delete the extra accounts, then run migrate again."
        )

    for address, rows in by_address.items():
        pk, email = rows[0]
        if email != address:
            User.objects.using(db).filter(pk=pk).update(email=address)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_user_token_version"),
    ]

    operations = [
        migrations.RunPython(lowercase_emails, migrations.RunPython.noop),
    ]
