from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from scans.models import Scan

User = get_user_model()

def transfer_guest_scans(guest_token, target_user):
    """
    Move every scan owned by the guest identified by `guest_token` over to `target_user`, then delete the guest account. Returns how many scans moved.

    Call this only after `target_user` has proven who they are (for example, after a correct password). It never raises for a bad token: a missing, expired or unusable token, or one that does not belong to a guest account, simply means there is nothing to transfer  and 0 is returned.

    Only accounts still flaged as guests can be emptied this way, so a real account's scans can never be moved out through this function.
    """
    if not guest_token:
        return 0

    try:
        # Checks the signature, the expiry and that this is an access token.
        token = AccessToken(guest_token)
        guest_id = int(token['user_id'])
    except (TokenError, KeyError, TypeError, ValueError):
        return 0

    if guest_id == target_user.pk:
        return 0

    # One all-or-nothing step. The row lock stops two requests from moving the same guest's scans twice (it takes effect on Postgres).
    with transaction.atomic():
        guest = User.objects.select_for_update().filter(pk=guest_id, is_guest=True).first()
        if guest is None:
            return 0

        moved = Scan.objects.filter(user=guest).update(user=target_user)
        guest.delete()

    return moved

