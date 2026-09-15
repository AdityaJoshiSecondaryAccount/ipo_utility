import logging
from django.contrib.auth import get_user_model
from django.utils import timezone

from home.models import CurrentIpoName, GroupDetail, Order, OrderDetail

logger = logging.getLogger(__name__)
User = get_user_model()


def get_default_user():
    """Returns the primary superuser or first active user to own the order."""
    superuser = User.objects.filter(is_superuser=True, is_active=True).first()
    if not superuser:
        superuser = User.objects.filter(is_active=True).first()
    return superuser


def get_or_create_customer_group(phone_number: str, user):
    """
    Finds existing GroupDetail by phone number, or auto-creates a group for the WhatsApp customer.
    """
    if not phone_number:
        phone_number = "UNKNOWN"

    clean_number = "".join(filter(str.isdigit, phone_number))
    last10 = clean_number[-10:] if len(clean_number) >= 10 else clean_number

    # Try matching existing GroupDetail
    group = GroupDetail.objects.filter(MobileNo__endswith=last10, Active=True).first()
    if not group:
        group_name = f"WA_{last10}" if last10 else "WA_CUSTOMER"
        group = GroupDetail.objects.create(
            user=user,
            GroupName=group_name,
            MobileNo=last10,
            Active=True,
        )
        logger.info(f"Auto-created GroupDetail #{group.id} ({group_name}) for phone {phone_number}")

    return group


def handle_flow_action(decrypted_payload: dict, customer_phone: str = None) -> dict:
    """
    Processes decrypted WhatsApp Flow requests and routes to the appropriate response screen.
    
    Actions handled:
    - 'ping' -> Meta Endpoint Health Check
    - 'INIT' -> Flow launch, returns active IPO list
    - 'data_exchange' -> Screen transitions & order creation
    - 'BACK' -> Navigation
    """
    action = decrypted_payload.get("action")
    screen = decrypted_payload.get("screen")
    data = decrypted_payload.get("data", {})
    flow_token = decrypted_payload.get("flow_token")

    logger.info(f"Flow Request: action={action}, screen={screen}, flow_token={flow_token}")

    # 1. Health Check Ping from Meta Flow Builder
    if action == "ping":
        return {
            "data": {
                "status": "active"
            }
        }

    # 2. Client error notification acknowledgment
    if action == "data_exchange" and "error" in data:
        logger.warning(f"WhatsApp Flow Error Notification: {data}")
        return {
            "data": {
                "acknowledged": True
            }
        }

    # 3. Flow Initial Launch (INIT action)
    if action == "INIT":
        active_ipos = CurrentIpoName.objects.filter(Active=True).order_by("-id")
        ipo_list = []
        for ipo in active_ipos:
            ipo_list.append({
                "id": str(ipo.id),
                "title": ipo.IPOName.strip()
            })

        if not ipo_list:
            ipo_list.append({
                "id": "0",
                "title": "No Active IPOs Available"
            })

        return {
            "screen": "IPO_SELECT",
            "data": {
                "side": "BUY",
                "ipo_list": ipo_list
            }
        }

    # 4. Data Exchange (Order submission from CONFIRM screen)
    if action == "data_exchange":
        place_order_action = data.get("action")

        if place_order_action == "place_order" or screen == "CONFIRM":
            return process_order_placement(data, customer_phone)

        # Default fallback response for intermediate data exchanges
        return {
            "screen": screen or "IPO_SELECT",
            "data": data
        }

    # 5. Back action
    if action == "BACK":
        return {
            "screen": screen or "IPO_SELECT",
            "data": data
        }

    # Generic fallback
    return {
        "screen": "IPO_SELECT",
        "data": {}
    }


def process_order_placement(data: dict, customer_phone: str = None) -> dict:
    """
    Validates and places BUY or SELL order into Django database models (Order & OrderDetail).
    """
    try:
        default_user = get_default_user()
        group = get_or_create_customer_group(customer_phone, default_user)
        user = group.user if (group and group.user) else default_user

        side = (data.get("side") or "BUY").upper()
        ipo_id = data.get("ipo_id")
        segment = data.get("segment") or "RETAIL"
        category = data.get("category") or "Kostak"
        quantity = float(data.get("quantity") or 0)
        rate = float(data.get("rate") or 0)
        strike_price = data.get("strike_price")
        remark_text = (data.get("remark") or "").strip()

        if not ipo_id or str(ipo_id) == "0":
            return {
                "screen": "COMPLETE",
                "data": {
                    "confirmation_text": "Error: No valid IPO was selected. Please try again."
                }
            }

        ipo = CurrentIpoName.objects.filter(id=int(ipo_id)).first()
        if not ipo:
            return {
                "screen": "COMPLETE",
                "data": {
                    "confirmation_text": f"Error: Selected IPO (ID: {ipo_id}) was not found or is inactive."
                }
            }

        now = timezone.localtime(timezone.now())
        order_date = now.date()
        order_time = now.time()

        # Build remark JSON
        remark_dict = {"source": "whatsapp_flow"}
        if remark_text:
            remark_dict["text"] = remark_text

        # Create Order record
        order = Order.objects.create(
            user=user,
            OrderGroup=group,
            OrderIPOName=ipo,
            OrderType=side,
            Rate=rate,
            Quantity=quantity,
            OrderCategory=category,
            Amount=rate * quantity,
            OrderDate=order_date,
            OrderTime=order_time,
            InvestorType=segment,
            Method=str(strike_price) if strike_price else None,
            Active=True,
            remark=remark_dict,
        )

        # Bulk create OrderDetail records
        qty_int = int(quantity)
        if qty_int > 0:
            pre_open_price = getattr(ipo, "PreOpenPrice", 0) or 0
            OrderDetail.objects.bulk_create([
                OrderDetail(
                    user=user,
                    Order=order,
                    PreOpenPrice=pre_open_price,
                    Amount=0,
                    Active=True,
                )
                for _ in range(qty_int)
            ])

        logger.info(f"Successfully placed {side} Order #{order.id} for {ipo.IPOName} (Qty: {quantity}, Rate: {rate}) via WhatsApp Flow.")

        # Send WhatsApp Confirmation Message to customer chat
        target_phone = customer_phone or getattr(group, "MobileNo", "")
        if target_phone:
            clean_phone = "".join(filter(str.isdigit, target_phone))
            if len(clean_phone) == 10:
                clean_phone = "91" + clean_phone

            if len(clean_phone) >= 11:
                try:
                    from .client import send_text_message
                    wa_message = (
                        f"🎉 *Order Confirmation*\n\n"
                        f"Your *{side}* order has been placed successfully!\n\n"
                        f"📋 *Order ID:* #{order.id}\n"
                        f"🏢 *IPO:* {ipo.IPOName}\n"
                        f"👥 *Group:* {group.GroupName}\n"
                        f"📦 *Segment:* {segment}\n"
                        f"🏷️ *Category:* {category}\n"
                        f"🔢 *Quantity:* {int(quantity)} lot(s)\n"
                        f"💰 *Rate:* ₹{rate}\n"
                        f"📅 *Date & Time:* {order_date.strftime('%d-%m-%Y')} {order_time.strftime('%H:%M:%S')}"
                    )
                    if remark_text:
                        wa_message += f"\n📝 *Remark:* {remark_text}"

wa_res = send_text_message(clean_phone, wa_message)
                    logger.info(f"WhatsApp order confirmation sent to {clean_phone}: HTTP {wa_res.status_code}")
                    
                    # ALSO send the status image immediately after text confirmation
                    try:
                        from .client import upload_media, send_image_message
                        from .services import build_order_summary_context, generate_order_summary_image
                        
                        orders = Order.objects.filter(OrderGroup=group, OrderIPOName=ipo, Active=True)
                        img_context = build_order_summary_context(group=group, orders=orders, ipo=ipo)
                        img_buf = generate_order_summary_image(img_context)
                        
                        if img_buf:
                            upload_res = upload_media(img_buf, mime_type="image/png", filename="status_report.png")
                            if upload_res.ok:
                                media_id = upload_res.json().get('id')
                                send_image_message(clean_phone, media_id=media_id, caption=f"{ipo.IPOName} Status - {group.GroupName}")
                                logger.info(f"WhatsApp order status image sent to {clean_phone}")
                            else:
                                logger.error(f"Failed to upload status image to WhatsApp: {upload_res}")
                    except Exception as img_err:
                        logger.error(f"Error generating/sending order status image to {clean_phone}: {img_err}")

                except Exception as send_err:
                    logger.error(f"Error sending WhatsApp confirmation message to {clean_phone}: {send_err}")

        flow_confirmation = (
            f"Thank you! Your {side} order for {ipo.IPOName} (Qty: {int(quantity)}, Rate: ₹{rate}) "
            f"has been submitted successfully.\n\n"
            f"An order confirmation message has been sent to your WhatsApp chat."
        )

        return {
            "screen": "COMPLETE",
            "data": {
                "confirmation_text": flow_confirmation
            }
        }

    except Exception as e:
        logger.error(f"Failed to place order via WhatsApp Flow: {e}", exc_info=True)
        return {
            "screen": "COMPLETE",
            "data": {
                "confirmation_text": f"Error placing order: {str(e)}"
            }
        }

