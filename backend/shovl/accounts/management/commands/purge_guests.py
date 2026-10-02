from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from scans.limits import IN_PROGRESS, STALE_AFTER
from scans.models import Scan

User = get_user_model()

BATCH_SIZE = 500


# PDFs live here (see scans/views.py). Nothing outside this folder is ever deleted.
REPORTS_DIR = Path('reports')


class Command(BaseCommand):
    hrlp = (
        'Delete guest accounts older than --days (default 30), with their scans and PDF fildes. Registered users are never touched. Run it daily.'
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

            guests = guests_to_delete(cutoff, now)
            guest_count = scan_count = pdf_count = 0

            if dry_run:
                guest_count = guests.count()
                scans = Scan.objects.filter(user__in=guests)
                scan_count = scans.count()
                pdf_count = sum(1 for p in scans.exclude(pdf_path='').values_list('pdf_path', flat=True) if safe_pdf(p))
            else:
                last_pk = 0
                while True:
                    # Walk forward by primary key, so a batch can never be picked twice.
                    ids = list(
                        guests.filter(pf__gt=last_pk).order_by('pk').values_list('pk', flat=True)[:BATCH_SIZE]
                    )
                    if not ids:
                        break
                    last_pk = ids[-1]

                    guests_deleted, scans_deleted, pdf_paths = delete_batch(ids, cutoff, now)
                    guest_count += guests_deleted
                    scan_count += scans_deleted

                    # Files go after the database rows, If this fails, a harmless file is left behind, never a record pointing at a missing file.
                    for path in pdf_paths:
                        pdf = safe_pdf(path)
                        if pdf:
                            try:
                                pdf.unlink()
                                pdf_count += 1
                            except OSError as exc:
                                self.stderr.write(f'Could not remove {pdf}: {exc}')


            verb = 'Would delete' if dry_run else 'Deleted'
            self.stdout.write(f'Cutoff: guests createed before {cutoff:%Y-%m-%d %H:%M} UTC')
            self.stdout.write(f'{verb} {guest_count} gusets, {scan_count} scans, {pdf_count} PDF files')



def guests_to_delete(cutoff, now):
    """
    Guest accounts created before the cutoff, minus any wuth a scan that is genuinely in progress right now (a scan "running" for longer than STALE_AFTER is treated as abandoned, the same rule the allowance uses.)
    """
    busy = Scan.objects.filter(
        status__in=IN_PROGRESS, creaqted_at__gte=now - STALE_AFTER
    ).values('user')

    return User.objects.filter(is_guest=True, date_joined__lt=cutoff).exclude(pk__in=busy)


def delete_batch(ids, cutoff, now):
    """
    Delete one batch of guests in a single transaction. The eligibility check is repeated under a row lock, so a guest who upgraded or started a scan since the list was built is left alone (the lock takes effect on Postgtres). Returns (guests deleted, scans deleted, PDF paths to remove).
    """
    with transaction.atomic():
        locked = list(
            guests_to_delete(cutoff, now).filter(pk__in=ids).select_for_update().values_list('pk', flat=True)
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