from django.http import HttpResponse
from django.shortcuts import redirect
from django.contrib import messages


def allowed_users(allowed_roles=[]):
    def decorator(view_func):
        def wrapper_func(request, *args, **kwargs):

            group = None
            # if request.user.groups.exists():
            if request.user.is_anonymous:
                messages.error(
                request, 'Your session is expired. Please log in again.')
                return redirect("/login")
            group = request.user.groups.all()[0].name
            if group in allowed_roles:
                return view_func(request, *args, **kwargs)
            else:
                return HttpResponse('You are not authorized to view this page')
        return wrapper_func
    return decorator


def Broker_only(view_func):
    def wrapper_function(request, *args, **kwargs):
        group = None
        if request.user.groups.exists():
            group = request.user.groups.all()[0].name

        if group == 'Customer':
            return redirect('/indexforCustomer')

        if group == 'Broker':
            return view_func(request, *args, **kwargs)
        return redirect('login')
    return wrapper_function
