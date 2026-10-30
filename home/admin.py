from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.conf import settings
from .models import (
    CustomUser, CurrentIpoName, GroupDetail, OrderDetail, ClientDetail, Order, RateList
)


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = CustomUser

    def clean_two_factor_enabled(self):
        enabled = self.cleaned_data.get('two_factor_enabled')
        # Admin can only turn OFF 2FA. Admin cannot turn ON 2FA.
        if self.instance and self.instance.pk:
            if not self.instance.two_factor_enabled and enabled:
                raise forms.ValidationError(
                    "Admins cannot enable 2FA manually. The user must enable it themselves by scanning their QR code in their account settings."
                )
        elif enabled:
            raise forms.ValidationError(
                "Admins cannot enable 2FA manually. The user must enable it themselves by scanning their QR code in their account settings."
            )
        return enabled


class UserModel(UserAdmin):
    form = CustomUserChangeForm
    list_display = UserAdmin.list_display + (
        'two_factor_enabled', 'IPO_limit', 'Order_limit', 'Premium_Order_limit',
        'Client_limit', 'Group_limit', 'Allotment_access', 'Expiry_Date', 'AppPassword', 'TelegramApi_id', 'TelegramApi_key', 'Mobileno', 'Telegram_session'
    )
    list_filter = UserAdmin.list_filter + ('two_factor_enabled',)
    readonly_fields = ('two_factor_secret', 'backup_codes')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('IPO_limit', 'Order_limit', 'Premium_Order_limit', 'Client_limit', 'Group_limit', 'Allotment_access', 'Expiry_Date', 'AppPassword', 'TelegramApi_id', 'TelegramApi_key', 'Mobileno', 'Telegram_session')}),
        ('Two-Factor Authentication (2FA)', {
            'description': 'Admins can ONLY disable 2FA (to recover a locked-out user). 2FA can only be enabled by the user scanning their own QR code.',
            'fields': ('two_factor_enabled', 'two_factor_secret', 'backup_codes')
        }),
    )

    actions = ['disable_2fa_action']

    def save_model(self, request, obj, form, change):
        # If admin disabled 2FA, automatically clear secret and backup codes
        if change and 'two_factor_enabled' in form.changed_data and not obj.two_factor_enabled:
            obj.two_factor_secret = None
            obj.backup_codes = []
        super().save_model(request, obj, form, change)

    @admin.action(description="Disable 2FA for selected users (Reset)")
    def disable_2fa_action(self, request, queryset):
        count = queryset.update(
            two_factor_enabled=False,
            two_factor_secret=None,
            backup_codes=[]
        )
        self.message_user(
            request,
            f"Successfully disabled 2FA and reset keys for {count} user(s).",
            messages.SUCCESS
        )


admin.site.register(CustomUser, UserModel)
admin.site.register(CurrentIpoName)
admin.site.register(GroupDetail)
admin.site.register(OrderDetail)
admin.site.register(ClientDetail)
admin.site.register(Order)

if getattr(settings, 'IS_WEB', True):
    admin.site.register(RateList)
