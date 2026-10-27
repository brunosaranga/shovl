from rest_framework import permissions

REGISTRATION_REQUIRED_MESSAGE = {
    'detail': 'Create a free account to scan your own domain.',
    'code': 'registration_required',
}

EMAIL_UNCONFIRMED_MESSAGE = {
    'detail': 'Confirm your email first: type the 6-digit code we sent you.',
    'code': 'email_unconfirmed',
}


def account_block(user):
    """
    Why this account can't use its own domains yet (add, verify or scan them, murindzi,
    settings), as the 403 body to send, or None if it can. Guests need an account; accounts
    need a confirmed email (accounts/confirmation.py).
    """
    if user.is_guest:
        return REGISTRATION_REQUIRED_MESSAGE
    if user.email_confirmed_at is None:
        return EMAIL_UNCONFIRMED_MESSAGE
    return None


class IsRegisteredUser(permissions.BasePermission):
    """
    Signed-in accounts with a confirmed email. Guests and unconfirmed accounts don't count.

    A guest gets a 403 whose body carries `code: registration_required`, which the frontend
    uses to show the "create a free account" prompt; an unconfirmed account gets
    `code: email_unconfirmed`, which sends it to the code screen. Someone who is not signed in
    at all gets the usual 401.
    """
    message = REGISTRATION_REQUIRED_MESSAGE

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        block = account_block(user)
        if block:
            self.message = block
            return False
        return True
