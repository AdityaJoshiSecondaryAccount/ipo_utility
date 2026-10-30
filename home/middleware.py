from django.shortcuts import redirect
from django.conf import settings
from django.contrib import messages


class SessionExpiryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the session has expired
        if request.user.is_authenticated and not request.session.exists(request.session.session_key):
            # Log out the user if the session has expired
            from django.contrib.auth import logout
            logout(request)
            messages.error(
                request, 'Your session is expired. Please log in again.')
            return redirect('login')  # Replace 'login' with the name of your login URL

        response = self.get_response(request)
        return response
