from rest_framework import permissions

REGISTRATION_REQUIRED_MESSAGE = {
    'detail': 'Create a free account to scan your own domain.',
    'code': 'registration_required',
}


class IsRegisteredUser(permissions.BasePermission):
    """
    Signed-in users only, and guest accounts do not count.

    Aguest gets a 403 whose body carries `code: registration_required`, which the frontend uses to show the "create a free account" prompt. Someone who is not signed in at all gets the usual 401.
    """
    message = REGISTRATION_REQUIRED_MESSAGE

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and not user.is_guest)