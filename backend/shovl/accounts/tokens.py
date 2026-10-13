"""
Sign-in tokens that can be revoked.

Every token carries the account's token version in a "tv" claim. The
authentication class (accounts/authentication.py) rejects a token whose version
no longer matches the account's, so raising an account's version signs out every
token it was ever given. Upgrading a guest does this, which is what stops the old
30-day guest token from working on the registered account.

A token issued before this existed has no claim and counts as version 0, so
turning this on does not sign anyone out.
"""
from rest_framework_simplejwt.tokens import RefreshToken

TOKEN_VERSION_CLAIM = "tv"


def token_version_of(token):
    """The version stored in a token. Tokens without one count as version 0."""
    return token.get(TOKEN_VERSION_CLAIM, 0)


def issue_tokens(user, access_lifetime=None):
    """
    A new (access, refresh) pair for `user`, both stamped with the account's
    current token version. `access_lifetime` overrides how long the access token
    lasts (used for guests, who have no refresh flow).
    """
    refresh = RefreshToken.for_user(user)
    refresh[TOKEN_VERSION_CLAIM] = user.token_version
    access = refresh.access_token           # copies the version claim from the refresh token
    if access_lifetime is not None:
        access.set_exp(lifetime=access_lifetime)
    return str(access), str(refresh)