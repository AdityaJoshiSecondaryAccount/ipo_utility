import io
import os
import re
import shutil
import logging
from django.conf import settings
from django.db.models import Count, F, Q, Sum
from django.template.loader import render_to_string

from home.models import CurrentIpoName, GroupDetail, Order

logger = logging.getLogger(__name__)


def normalize_phone_number(value):
    """Normalize phone number to 91XXXXXXXXXX or standard international format."""
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) == 10:
        digits = "91" + digits
    return digits


def get_groups_by_phone(raw_phone):
    """Finds active GroupDetail record(s) matching the phone number."""
    if not raw_phone:
        return GroupDetail.objects.none()

    clean_phone = normalize_phone_number(raw_phone)
    last_10 = clean_phone[-10:] if len(clean_phone) >= 10 else clean_phone

    groups = GroupDetail.objects.filter(Active=True).filter(
        Q(MobileNo=clean_phone) |
        Q(MobileNo=last_10) |
        Q(MobileNo__endswith=last_10)
    )
    return groups


def get_orders_for_groups(groups, ipo_id=None):
    """Fetches active orders for the given groups."""
    queryset = Order.objects.filter(OrderGroup__in=groups, Active=True)
    if ipo_id:
        queryset = queryset.filter(OrderIPOName_id=ipo_id)
    return queryset



def build_order_summary_context(group, orders=None, ipo=None):
    from django.db.models import Sum, Count, F

    if orders is None:
        orders = Order.objects.filter(OrderGroup=group, Active=True)
        
    if ipo is None and orders.exists():
        first_order = orders.first()
        ipo = first_order.OrderIPOName
        
    if ipo and orders is not None:
        orders = orders.filter(OrderIPOName=ipo)

    IPO = ipo

    OrdCat = ['Kostak','SubjectTo','CALL','PUT']
    InvTyp = ['RETAIL','SHNI','BHNI','OPTIONS']
    OrdTyp = ['BUY','SELL']

    strike_dict = {}
    dict_count = {}
    dict_avg = {}
    dict_amount = {}

    aggregates = (
        orders
        .values("OrderType", "OrderCategory", "InvestorType", "Method")
        .annotate(
            total_qty=Sum("Quantity"),
            total_amt=Sum(F("Rate") * F("Quantity")),
            total_count=Count("id")
        )
    )
    
    agg_lookup = {}
    for row in aggregates:
        key = (row["OrderCategory"], row["InvestorType"], row["OrderType"], row["Method"])
        agg_lookup[key] = {
            "count": row["total_qty"] or 0,
            "amount": row["total_amt"] or 0,
            "entries": row["total_count"] or 0,
        }

    for ordertype in OrdTyp:
        for ordercategory in OrdCat:
            for investortype in InvTyp:
                key_category = "Subject To" if ordercategory == "SubjectTo" else ordercategory
                dict_key_prefix = f"{ordercategory}{investortype}{ordertype}"

                # Lookup (we don’t hit DB here)
                # NOTE: Method could vary (Premium/Normal/Strike etc.), so we loop over methods in agg_lookup
                matching_rows = [
                    v for k, v in agg_lookup.items()
                    if k[0] == key_category and k[1] == investortype and k[2] == ordertype
                ]

                # Aggregate amounts manually (still in memory, not DB)
                total_count = sum(v["count"] for v in matching_rows)
                total_amount = 0

                for (cat, inv, ot, method), v in agg_lookup.items():
                    if cat == key_category and inv == investortype and ot == ordertype:
                        # Apply your "Subject To" premium logic here
                        if cat == "Subject To" and method == "Premium":
                            if investortype == "RETAIL":
                                lot_size = IPO.LotSizeRetail
                            elif investortype == "SHNI":
                                lot_size = IPO.LotSizeSHNI
                            elif investortype == "BHNI":
                                lot_size = IPO.LotSizeBHNI
                            else:
                                lot_size = 1
                            total_amount += (lot_size * v["amount"])
                            
                        elif investortype == "OPTIONS" and ordercategory in ["CALL", "PUT"]:
                            
                            strike = method or "NA"

                            # Initialize dict structure
                            if strike not in strike_dict:
                                strike_dict[strike] = {
                                    "CALL": {"BUY": {"count":0,"amount":0,"avg":0,"net":0},
                                            "SELL":{"count":0,"amount":0,"avg":0 ,"net":0}},
                                    "PUT":  {"BUY": {"count":0,"amount":0,"avg":0 ,"net":0},
                                            "SELL":{"count":0,"amount":0,"avg":0 ,"net":0}}
                                }
                            # Update values
                            # strike_dict[strike][ordercategory][ordertype]["count"] += v.Quantity
                            # strike_dict[strike][ordercategory][ordertype]["amount"] += (v.Rate * v.Quantity)
                            strike_dict[strike][ordercategory][ordertype]["count"] += v["count"]
                            strike_dict[strike][ordercategory][ordertype]["amount"] += v["amount"]

                            # Calculate average
                            c = strike_dict[strike][ordercategory][ordertype]["count"]
                            a = strike_dict[strike][ordercategory][ordertype]["amount"]
                            strike_dict[strike][ordercategory][ordertype]["avg"] = (a / c) if c else 0
                            
                            # Net = (BUY amount - SELL amount) for that side
                            buy_amt  = strike_dict[strike][ordercategory]["BUY"]["amount"]
                            sell_amt = strike_dict[strike][ordercategory]["SELL"]["amount"]
                            strike_dict[strike][ordercategory]["BUY"]["net"]  = buy_amt - sell_amt
                            strike_dict[strike][ordercategory]["SELL"]["net"] = sell_amt - buy_amt
                            
                            # amount = (v.Rate * v.Quantity) + amount
                            total_amount += v["amount"]
                                
                        else:
                            total_amount += v["amount"]

                # Save into dicts
                dict_count[f"{dict_key_prefix}Count"] = total_count
                dict_avg[f"{dict_key_prefix}Avg"] = (total_amount / total_count) if total_count else 0
                dict_amount[f"{dict_key_prefix}Amount"] = total_amount
    net_count = {}
    net_avg = {}
    net_amount = {}
                    
    for ordercategory in OrdCat:
        for investortype in InvTyp:
            # Keys for BUY and SELL
            buy_key_count = f"{ordercategory}{investortype}BUYCount"
            sell_key_count = f"{ordercategory}{investortype}SELLCount"
            
            buy_key_avg = f"{ordercategory}{investortype}BUYAvg"
            sell_key_avg = f"{ordercategory}{investortype}SELLAvg"

            # Get counts (default 0 if missing)
            buy_count = dict_count.get(buy_key_count, 0)
            sell_count = dict_count.get(sell_key_count, 0)
            net_c = buy_count - sell_count

            # Get amounts (Count * Avg)
            buy_amount = buy_count * dict_avg.get(buy_key_avg, 0)
            sell_amount = sell_count * dict_avg.get(sell_key_avg, 0)
            net_amt = buy_amount - sell_amount

            # Calculate net average
            if net_c != 0:
                net_a = net_amt / net_c
            else:
                net_a = 0
                
            if net_c == 0:
                net_amt = sell_amount - buy_amount

            # Store results
            key_prefix = f"{ordercategory}{investortype}Net"
            net_count[f"{key_prefix}Count"] = net_c
            net_avg[f"{key_prefix}Avg"] = round(net_a, 2)
            net_amount[f"{key_prefix}Amount"] = round(net_amt, 2)
            
    PremiumBuyfilter = orders.filter(OrderType="BUY",OrderCategory="Premium")
    PremiumBuyCount11 = PremiumBuyfilter.aggregate(Sum('Quantity'))
    PremiumBuyCount1 = PremiumBuyCount11['Quantity__sum']
    if PremiumBuyCount1 == None:
        PremiumBuyCount = 0
    else:
        PremiumBuyCount = PremiumBuyCount1
    
    PremiumBuyAmount=0
    for i in PremiumBuyfilter:
        PremiumBuyAmount=(i.Quantity*i.Rate)+PremiumBuyAmount

    if PremiumBuyCount==0:
        PremiumBuyAvg=0    
    else:
        PremiumBuyAvg=PremiumBuyAmount/PremiumBuyCount
    
    PremiumSellfilter = orders.filter(OrderType="SELL",OrderCategory="Premium")
    PremiumSellCount11 = PremiumSellfilter.aggregate(Sum('Quantity'))
    PremiumSellCount1 = PremiumSellCount11['Quantity__sum']
    if PremiumSellCount1 == None:
        PremiumSellCount = 0
    else:
        PremiumSellCount = PremiumSellCount1

    PremiumSellAmount=0
    for i in PremiumSellfilter:
        PremiumSellAmount=(i.Quantity*i.Rate)+PremiumSellAmount

    if PremiumSellCount==0:
        PremiumSellAvg=0    
    else:
        PremiumSellAvg=PremiumSellAmount/PremiumSellCount
    
    PremiumNetCount = PremiumBuyCount - PremiumSellCount
    Premiumavg1 = PremiumBuyCount * PremiumBuyAvg
    Premiumavg2 = PremiumSellCount * PremiumSellAvg
    pri_net_avg = Premiumavg1 - Premiumavg2
    if PremiumNetCount != 0:
        PremiumNetAvg = pri_net_avg /PremiumNetCount
    else:
        PremiumNetAvg =  0
        
    PremiumNetAmount = PremiumBuyAmount - PremiumSellAmount
    strike_prices = []
    grand_call_count = grand_call_amount = grand_put_count = grand_put_amount = 0
    for strike, cats in strike_dict.items():
        # CALL
        call_buy_count = cats["CALL"]["BUY"]["count"]
        call_sell_count = cats["CALL"]["SELL"]["count"]
        call_buy_amount = cats["CALL"]["BUY"]["amount"]
        call_sell_amount = cats["CALL"]["SELL"]["amount"]
        
        call_net_count = call_buy_count - call_sell_count
        call_avg1 = call_buy_amount - call_sell_amount
        call_avg2 = call_sell_amount - call_buy_amount
        call_net_avg = call_avg1 - call_avg2
        # call_net_amount = call_buy_amount - call_sell_amount
        if call_net_count != 0:
            call_avg = call_net_avg / call_net_count
            call_net_amount = call_buy_amount - call_sell_amount
        else:
            call_avg = 0
            call_net_amount = call_sell_amount - call_buy_amount
        # PUT
        put_buy_count = cats["PUT"]["BUY"]["count"]
        put_sell_count = cats["PUT"]["SELL"]["count"]
        put_buy_amount = cats["PUT"]["BUY"]["amount"]
        put_sell_amount = cats["PUT"]["SELL"]["amount"]

        put_net_count = put_buy_count - put_sell_count
        put_avg1 = put_buy_amount - put_sell_amount
        put_avg2 = put_sell_amount - put_buy_amount
        put_net_avg = put_avg1 - put_avg2
        # put_net_amount = put_buy_amount - put_sell_amount 
        if put_net_count != 0:
            put_avg = put_net_avg / put_net_count
            put_net_amount = put_buy_amount - put_sell_amount
        else:
            put_avg = 0 
            put_net_amount = put_sell_amount - put_buy_amount
        
        strike_prices.append({
            "value": strike,
            "call_total_count": call_net_count,
            "call_avg": (call_net_amount / call_net_count) if call_net_count else 0,
            "call_net_amount": call_net_amount,
            "put_total_count": put_net_count,
            "put_avg": (put_net_amount / put_net_count) if put_net_count else 0,
            "put_net_amount": put_net_amount,
        })
        
        grand_call_count += call_net_count
        grand_call_amount += call_net_amount
        grand_put_count += put_net_count
        grand_put_amount += put_net_amount
    grand_total = {
        "call_total_count": grand_call_count,
        "call_avg": (grand_call_amount/grand_call_count ) if grand_call_count else 0,
        "call_net_amount": grand_call_amount,
        "put_total_count": grand_put_count,
        "put_avg": grand_put_amount/grand_put_count if grand_put_count else 0,
        "put_net_amount": grand_put_amount,
    }
    
    
    category_totals = {
        "CALL": {"count": grand_call_count, "avg": grand_total["call_avg"]},
        "PUT":  {"count": grand_put_count, "avg": grand_total["put_avg"]},
    }

    context = {
        'IPOName': IPO,
        'strike_prices': strike_prices,
        'grand_total': grand_total,
        'category_totals': category_totals,
        'PremiumBuyAmount': PremiumBuyAmount,
        'PremiumNetAmount': PremiumNetAmount,
        'PremiumSellAmount': PremiumSellAmount,
        'dict_count': dict_count,
        'net_count': net_count,
        'net_avg': net_avg,
        'net_amount': net_amount,
        'dict_amount': dict_amount,
        'dict_avg': dict_avg,
        'PremiumNetCount': "{:.2f}".format(PremiumNetCount) if isinstance(PremiumNetCount, float) else str(PremiumNetCount),
        'PremiumNetAvg': "{:.2f}".format(PremiumNetAvg),
        'PremiumBuyCount': PremiumBuyCount,
        'PremiumSellCount': PremiumSellCount,
        'PremiumSellAvg': "{:.2f}".format(PremiumSellAvg),
        'PremiumBuyAvg': "{:.2f}".format(PremiumBuyAvg),
    }
    return context




def get_wkhtmltoimage_config():
    import sys, shutil, os, imgkit
    from django.conf import settings
    exe = shutil.which('wkhtmltoimage') or shutil.which('wkhtmltoimage.exe')
    if exe:
        try:
            return imgkit.config(wkhtmltoimage=exe)
        except Exception:
            pass
    possible_paths = [
        os.path.join(getattr(sys, '_MEIPASS', ''), 'wkhtmltoimage.exe'),
        os.path.join(settings.BASE_DIR, 'wkhtmltoimage.exe'),
        os.path.join(settings.BASE_DIR, 'wkhtmltoimage'),
        r'C:\Program Files\wkhtmltopdf\bin\wkhtmltoimage.exe',
        r'/usr/bin/wkhtmltoimage',
    ]
    for p in possible_paths:
        if p and os.path.exists(p):
            try:
                return imgkit.config(wkhtmltoimage=p)
            except Exception:
                pass
    return None

def generate_order_summary_image(context):
    from django.template.loader import render_to_string
    import imgkit, io, logging
    logger = logging.getLogger(__name__)
    html = render_to_string('status_table_template.html', context)
    options = {'format': 'png', 'quality': '100', 'encoding': 'UTF-8'}
    config = get_wkhtmltoimage_config()
    
    if config:
        img_bytes = imgkit.from_string(html, False, options=options, config=config)
    else:
        try:
            img_bytes = imgkit.from_string(html, False, options=options)
        except Exception as e:
            logger.error('imgkit error: %s', e)
            return _generate_fallback_image(context)
            
    buf = io.BytesIO(img_bytes)
    buf.name = 'status_report.png'
    return buf

def _generate_fallback_image(context):
    """Creates a clean image report using Pillow when wkhtmltoimage is not installed."""
    from PIL import Image, ImageDraw, ImageFont

    img_width = 850
    img_height = 550
    image = Image.new("RGB", (img_width, img_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Header
    draw.rectangle([(0, 0), (img_width, 50)], fill=(40, 60, 80))
    draw.text((img_width // 2 - 80, 15), "ORDERS SUMMARY", fill=(255, 255, 255))

    # Categories Summary
    y = 70
    dict_count = context.get('dict_count', {})
    dict_amount = context.get('dict_amount', {})
    net_count = context.get('net_count', {})

    categories = [
        ("Kostak Retail", dict_count.get("KostakRETAILBUYCount", 0), dict_count.get("KostakRETAILSELLCount", 0), net_count.get("KostakRETAILNetCount", 0)),
        ("Kostak SHNI", dict_count.get("KostakSHNIBUYCount", 0), dict_count.get("KostakSHNISELLCount", 0), net_count.get("KostakSHNINetCount", 0)),
        ("Kostak BHNI", dict_count.get("KostakBHNIBUYCount", 0), dict_count.get("KostakBHNISELLCount", 0), net_count.get("KostakBHNINetCount", 0)),
        ("Subject To Retail", dict_count.get("SubjectToRETAILBUYCount", 0), dict_count.get("SubjectToRETAILSELLCount", 0), net_count.get("SubjectToRETAILNetCount", 0)),
        ("Subject To SHNI", dict_count.get("SubjectToSHNIBUYCount", 0), dict_count.get("SubjectToSHNISELLCount", 0), net_count.get("SubjectToSHNINetCount", 0)),
        ("Subject To BHNI", dict_count.get("SubjectToBHNIBUYCount", 0), dict_count.get("SubjectToBHNISELLCount", 0), net_count.get("SubjectToBHNINetCount", 0)),
        ("Premium", context.get("PremiumBuyCount", 0), context.get("PremiumSellCount", 0), context.get("PremiumNetCount", 0)),
    ]

    # Table headers
    draw.rectangle([(30, y), (820, y + 25)], fill=(230, 235, 245))
    draw.text((40, y + 5), "CATEGORY", fill=(0, 0, 0))
    draw.text((320, y + 5), "BUY QTY", fill=(0, 0, 0))
    draw.text((500, y + 5), "SELL QTY", fill=(0, 0, 0))
    draw.text((680, y + 5), "NET QTY", fill=(0, 0, 0))
    y += 30

    for cat_name, buy_q, sell_q, net_q in categories:
        draw.rectangle([(30, y), (820, y + 25)], outline=(220, 220, 220), fill=(255, 255, 255))
        draw.text((40, y + 5), str(cat_name), fill=(30, 30, 30))
        draw.text((320, y + 5), str(buy_q), fill=(0, 100, 0))
        draw.text((500, y + 5), str(sell_q), fill=(150, 0, 0))
        draw.text((680, y + 5), str(net_q), fill=(0, 0, 150))
        y += 28

    # Options Strike table if available
    strike_prices = context.get('strike_prices', [])
    if strike_prices:
        y += 15
        draw.text((40, y), "OPTIONS / STRIKE PRICES", fill=(0, 0, 0))
        y += 25
        draw.rectangle([(30, y), (820, y + 25)], fill=(230, 235, 245))
        draw.text((40, y + 5), "STRIKE", fill=(0, 0, 0))
        draw.text((250, y + 5), "CALL NET QTY", fill=(0, 0, 0))
        draw.text((550, y + 5), "PUT NET QTY", fill=(0, 0, 0))
        y += 30
        for sp in strike_prices[:5]:
            draw.rectangle([(30, y), (820, y + 22)], outline=(220, 220, 220), fill=(255, 255, 255))
            draw.text((40, y + 4), str(sp.get("value")), fill=(30, 30, 30))
            draw.text((250, y + 4), str(sp.get("call_total_count")), fill=(0, 0, 0))
            draw.text((550, y + 4), str(sp.get("put_total_count")), fill=(0, 0, 0))
            y += 24

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    buf.name = "orders_summary.png"
    return buf
