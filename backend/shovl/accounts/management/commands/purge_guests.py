from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import EmailCode
from mailer.models import SentEmail
from scans.limits import IN_PROGRESS, STALE_AFTER
from scans.models import Scan

User = get_user_model()

BATCH_SIZE = 500

# The record of emails sent (mailer/models.py, SentEmail) is kept this long, then deleted here.
EMAIL_LOG_DAYS = 90

# Expired email codes (accounts/models.py, EmailCode) are useless; they go after a day.
EMAIL_CODE_DAYS = 1


# PDFs live here (see scans/views.py). Nothing outside this folder is ever deleted.
REPORTS_DIR = Path('reports')


class Command(BaseCommand):
    help = (
        'Delete guest accounts older than --days (default 30), and accounts that signed up but '
        'never confirmed their email by their deadline (7 days), with their scans and PDF files; '
        'also email log entries older than 90 days and expired email codes. Confirmed accounts, '
        'staff, and accounts from before email confirmation existed are never touched. Run it daily.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='Delete guests created more than this many days ago (default 30).')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without deleting anything.')

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']

        if days < 1:
            raise CommandError('--days must be at least 1.')

        now = timezone.now()
        cutoff = now - timedelta(days=days)
        verb = 'Would delete' if dry_run else 'Deleted'

        guests = self.purge(lambda: guests_to_delete(cutoff, now), dry_run)
        unconfirmed = self.purge(lambda: unconfirmed_to_delete(now), dry_run)

        old_emails = SentEmail.objects.filter(created_at__lt=now - timedelta(days=EMAIL_LOG_DAYS))
        old_codes = EmailCode.objects.filter(expires_at__lt=now - timedelta(days=EMAIL_CODE_DAYS))
        if dry_run:
            email_count = old_emails.count()
            code_count = old_codes.count()
        else:
            email_count, _ = old_emails.delete()
            code_count, _ = old_codes.delete()

        self.stdout.write(f'Cutoff: guests created before {cutoff:%Y-%m-%d %H:%M} UTC')
        self.stdout.write(f'{verb} {guests[0]} guests, {guests[1]} scans, {guests[2]} PDF files')
        self.stdout.write(
            f'{verb} {unconfirmed[0]} unconfirmed accounts past their deadline, '
            f'{unconfirmed[1]} scans, {unconfirmed[2]} PDF files'
        )
        self.stdout.write(f'{verb} {email_count} email log entries older than {EMAIL_LOG_DAYS} days')
        self.stdout.write(f'{verb} {code_count} expired email codes')

    def purge(self, eligible, dry_run):
        """
        Delete (or, on a dry run, count) the accounts `eligible()` returns, with their scans and
        PDF files. Returns (accounts, scans, PDF files).
        """
        if dry_run:
            accounts = eligible()
            scans = Scan.objects.filter(user__in=accounts)
            pdfs = sum(1 for p in scans.exclude(pdf_path='').values_list('pdf_path', flat=True) if safe_pdf(p))
            return accounts.count(), scans.count(), pdfs

        account_count = scan_count = pdf_count = 0
        last_pk = 0
        while True:
            # Walk forward by primary key, so a batch can never be picked twice.
            ids = list(
                eligible().filter(pk__gt=last_pk).order_by('pk').values_list('pk', flat=True)[:BATCH_SIZE]
            )
            if not ids:
                break
            last_pk = ids[-1]

            accounts_deleted, scans_deleted, pdf_paths = delete_batch(eligible, ids)
            account_count += accounts_deleted
            scan_count += scans_deleted

            # Files go after the database rows. If this fails, a harmless file is left behind, never a record pointing at a missing file.
            for path in pdf_paths:
                pdf = safe_pdf(path)
                if pdf:
                    try:
                        pdf.unlink()
                        pdf_count += 1
                    except OSError as exc:
                        self.stderr.write(f'Could not remove {pdf}: {exc}')

        return account_count, scan_count, pdf_count


def busy_accounts(now):
    """Accounts with a scan genuinely in progress right now (one "running" for longer than STALE_AFTER is treated as abandoned, the same rule the allowance uses)."""
    return Scan.objects.filter(
        status__in=IN_PROGRESS, created_at__gte=now - STALE_AFTER
    ).values('user')


def guests_to_delete(cutoff, now):
    """Guest accounts created before the cutoff, minus any with a scan in progress."""
    return User.objects.filter(is_guest=True, date_joined__lt=cutoff).exclude(pk__in=busy_accounts(now))


def unconfirmed_to_delete(now):
    """
    Accounts that signed up (or upgraded from a guest) and let their confirm_by pass without
    confirming the address (accounts/confirmation.py). Accounts from before confirmation
    existed have no confirm_by and are never picked; nor are staff, whatever the fields say.
    """
    return (
        User.objects.filter(
            is_guest=False,
            is_staff=False,
            is_superuser=False,
            email_confirmed_at__isnull=True,
            confirm_by__isnull=False,
            confirm_by__lt=now,
        )
        .exclude(pk__in=busy_accounts(now))
    )


def delete_batch(eligible, ids):
    """
    Delete one batch of accounts in a single transaction. The eligibility check is repeated under a row lock, so an account that upgraded, confirmed or started a scan since the list was built is left alone (the lock takes effect on Postgres). Returns (accounts deleted, scans deleted, PDF paths to remove).
    """
    with transaction.atomic():
        locked = list(
            eligible().filter(pk__in=ids).select_for_update().values_list('pk', flat=True)
        )
        if not locked:
            return 0, 0, []

        pdf_paths = list(
            Scan.objects.filter(user__in=locked).exclude(pdf_path='').values_list('pdf_path', flat=True)
        )
        _, per_model = User.objects.filter(pk__in=locked).delete()

    return per_model.get(User._meta.label, 0), per_model.get(Scan._meta.label, 0), pdf_paths


def safe_pdf(path):
    """The file as a Path if it exists and sits inside the reports folder, otherwise None."""
    try:
        pdf = Path(path).resolve()
        if REPORTS_DIR.resolve() in pdf.parents and pdf.is_file():
            return pdf
    except (OSError, ValueError):
        pass
    return None
