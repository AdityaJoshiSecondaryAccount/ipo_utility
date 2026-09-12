import re

import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from home.models import CurrentIpoName, GroupDetail

from .client import send_order_confirmation


ORDER_DETAIL_FIELDS = (
    ("Kostak Retail", "KostakQTY", "KostakRate"),
    ("Kostak SHNI", "KostakQTYSHNI", "KostakRateSHNI"),
    ("Kostak BHNI", "KostakQTYBHNI", "KostakRateBHNI"),
    ("Subject To Retail", "SubjectToQTY", "SubjectToRate"),
    ("Subject To SHNI", "SubjectToQTYSHNI", "SubjectToRateSHNI"),
    ("Subject To BHNI", "SubjectToQTYBHNI", "SubjectToRateBHNI"),
    ("Premium", "PremiumQTY", "PremiumRate"),
    ("Call", "CallQTY", "CallRate"),
    ("Put", "PutQTY", "PutRate"),
)


def _whatsapp_number(value):
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 10:
        digits = "91" + digits
    return digits


def _order_details(post_data):
    details = []
    for label, quantity_field, rate_field in ORDER_DETAIL_FIELDS:
        quantity = (post_data.get(quantity_field) or "").strip()
        rate = (post_data.get(rate_field) or "").strip()
        if quantity or rate:
            parts = [label]
            if quantity:
                parts.append(f"Qty: {quantity}")
            if rate:
                parts.append(f"Rate: {rate}")
            details.append(" - ".join(parts))
    return "; ".join(details)


def _send_order(request, ipo_id, order_type):
    required_settings = (
        "WHATSAPP_API_VERSION",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_ACCESS_TOKEN",
    )
    missing = [name for name in required_settings if not getattr(settings, name, "")]
    if missing:
        messages.error(request, "Order placed successfully, but WhatsApp is not configured.")
        return JsonResponse({
            "status": "error",
            "message": "WhatsApp API is not configured.",
        }, status=503)

    group_name = (request.POST.get("item_id") or "").strip()
    if not group_name:
        messages.error(request, "Order placed successfully, but no group was selected for WhatsApp.")
        return JsonResponse({"status": "error", "message": "Select a group first."}, status=400)

    group = get_object_or_404(
        GroupDetail,
        user=request.user,
        GroupName=group_name,
        Active=True,
    )
    phone_number = _whatsapp_number(group.MobileNo)
    if len(phone_number) < 11 or len(phone_number) > 15:
        messages.error(
            request,
            f"Order placed successfully, but {group.GroupName} has no valid mobile number.",
        )
        return JsonResponse({
            "status": "error",
            "message": f"Add a valid mobile number for {group.GroupName}.",
        }, status=400)

    ipo = get_object_or_404(CurrentIpoName, id=ipo_id, user=request.user)
    details = _order_details(request.POST)
    if not details:
        messages.error(request, "Order placed successfully, but WhatsApp order details were empty.")
        return JsonResponse({
            "status": "error",
            "message": "Enter at least one order quantity or rate.",
        }, status=400)

    try:
        response = send_order_confirmation(
            phone_number=phone_number,
            ipo_name=ipo.IPOName,
            order_type=order_type,
            group_name=group.GroupName,
            order_datetime=request.POST.get("datetime", ""),
            order_details=details,
        )
        response_data = response.json() if response.content else {}
    except requests.RequestException as exc:
        messages.error(request, "Order placed successfully, but the WhatsApp message failed.")
        return JsonResponse({
            "status": "error",
            "message": f"Unable to contact WhatsApp: {exc}",
        }, status=502)
    except ValueError:
        response_data = {}
    except Exception:
        messages.error(request, "Order placed successfully, but the WhatsApp message failed.")
        return JsonResponse({
            "status": "error",
            "message": "Unexpected error while sending the WhatsApp message.",
        }, status=502)

    if not response.ok:
        api_error = (
            response_data.get("error", {}).get("message")
            if isinstance(response_data, dict)
            else None
        )
        messages.error(request, "Order placed successfully, but the WhatsApp message failed.")
        return JsonResponse({
            "status": "error",
            "message": api_error or "WhatsApp rejected the message.",
        }, status=response.status_code if 400 <= response.status_code < 600 else 502)

    messages.success(request, "Order placed and WhatsApp message sent successfully.")
    return JsonResponse({"status": "success", "message": "WhatsApp message sent."})


@login_required
@require_POST
def send_buy_order(request, ipo_id):
    return _send_order(request, ipo_id, "BUY")


@login_required
@require_POST
def send_sell_order(request, ipo_id):
    return _send_order(request, ipo_id, "SELL")

