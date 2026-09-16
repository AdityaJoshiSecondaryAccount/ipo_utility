from django.apps import AppConfig
from django.db.models.signals import pre_save


class WhatsAppConfig(AppConfig):
    name = "whatsapp"

    def ready(self):
        try:
            from home.models import Order

            def sanitize_order_time(sender, instance, **kwargs):
                if instance.OrderTime and getattr(instance.OrderTime, "microsecond", 0) != 0:
                    instance.OrderTime = instance.OrderTime.replace(microsecond=0)

            pre_save.connect(sanitize_order_time, sender=Order, weak=False)
        except Exception:
            pass

