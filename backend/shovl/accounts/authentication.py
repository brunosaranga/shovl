from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .tokens import token_version_of


class VersionedJWTAuthentication(JWTAuthentication):
    """
    The normal JWT check, plus: the token's version must match the account's
    current token version. A token from before the account was upgraded (or
    otherwise had its tokens revoked) is refused with a 401, like an expired one.
    """

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if token_version_of(validated_token) != user.token_version:
            raise AuthenticationFailed(
                "This session is no longer valid. Please sign in again.",
                code="token_revoked",
            )
        return user