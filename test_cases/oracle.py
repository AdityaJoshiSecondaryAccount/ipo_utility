"""
Independent re-implementation of the billing / settlement formulas, shared by the Billing and
Status page tests. It deliberately does NOT import anything from home.views: the point is to check
the application's numbers against a second, separately written implementation.

IPO price P, pre-open price O, rate R, allotted quantity Q, order quantity N, strike K:
  Kostak     BUY  ((O - P) * Q) - R                    SELL  -(BUY)       Q None -> 0   (Q = 0 -> -R / +R)
  Subject To BUY  ((O - P) * Q) - R                    SELL  -(BUY)       Q None or 0 -> 0
             Premium method: the cost is R * Q instead of R
  Premium    BUY  (O - (P + R)) * N                    SELL  -(BUY)
  CALL  BUY  -R*N + max((O - (P+K))*N, 0)    SELL  +R*N + min((P+K-O)*N, 0)
  PUT   BUY  -R*N + max((P+K-O)*N, 0)        SELL  +R*N + min((O-(P+K))*N, 0)
Kostak / Subject To amounts belong to each OrderDetail (application); Premium / CALL / PUT to the Order.
"""
import datetime

from home.models import ClientDetail, GroupDetail, Order, OrderDetail

SEED_DATE, SEED_TIME = datetime.date(2026, 1, 20), datetime.time(10, 0, 0)


def detail_amount(od, ipo):
    o = od.Order
    if o.OrderCategory not in ("Kostak", "Subject To") or od.AllotedQty is None:
        return 0.0
    q, rate, gain = float(od.AllotedQty), float(o.Rate), (float(od.PreOpenPrice) - float(ipo.IPOPrice))
    if o.OrderCategory == "Kostak":
        amount = gain * q - rate
    else:
        if q == 0:
            return 0.0
        amount = gain * q - (rate * q if o.Method == "Premium" else rate)
    return amount if o.OrderType == "BUY" else -amount


def order_amount(o, ipo):
    p, pre, n, rate = float(ipo.IPOPrice), float(ipo.PreOpenPrice), float(o.Quantity), float(o.Rate)
    buy = o.OrderType == "BUY"
    if o.OrderCategory == "Premium":
        amount = (pre - (p + rate)) * int(n)
        return amount if buy else -amount
    k = float(o.Method)
    if o.OrderCategory == "CALL":
        return (-rate * n + max((pre - (p + k)) * n, 0)) if buy else (rate * n + min((p + k - pre) * n, 0))
    return (-rate * n + max((p + k - pre) * n, 0)) if buy else (rate * n + min((pre - (p + k)) * n, 0))


def seed_specs(user, ipo, specs, pre_open):
    """
    Idempotent seeding. Kostak / Subject To: one OrderDetail per entry of `alloted` (None = not allotted);
    Premium / CALL / PUT: one order of `qty` shares (method = strike for options).
    """
    for s in specs:
        group = GroupDetail.objects.get_or_create(user=user, GroupName=s["group"])[0]
        if Order.objects.filter(user=user, OrderIPOName=ipo, OrderGroup=group, OrderType=s["type"],
                                OrderCategory=s["cat"], InvestorType=s["inv"], Rate=s["rate"],
                                Method=s.get("method")).exists():
            continue
        alloted = s.get("alloted")
        order = Order.objects.create(
            user=user, OrderIPOName=ipo, OrderGroup=group, OrderType=s["type"], OrderCategory=s["cat"],
            InvestorType=s["inv"], Rate=s["rate"], Quantity=len(alloted) if alloted is not None else s["qty"],
            Method=s.get("method"), OrderDate=SEED_DATE, OrderTime=SEED_TIME)
        for i, qty in enumerate(alloted or []):
            pan = (s.get("pans") or [None] * len(alloted))[i]
            client = None
            if pan:
                client = ClientDetail.objects.get_or_create(
                    user=user, PANNo=pan, defaults={"Name": "TEST CLIENT", "Group": group})[0]
            OrderDetail.objects.create(user=user, Order=order, AllotedQty=qty, PreOpenPrice=pre_open,
                                       OrderDetailPANNo=client)


# ------------------------------------------------------------------------------------------------
# Per-group position figures, shared by the Status and Positions page tests
# ------------------------------------------------------------------------------------------------
TIERS = ("RETAIL", "SHNI", "BHNI")


def avg_text(v):
    """The pages' average formatting: 4 decimals, trailing zeros removed, blank for 0."""
    if v is None or float(v or 0) == 0:
        return ""
    return f"{float(v):.4f}".rstrip("0").rstrip(".")


def group_figures(user, ipo):
    """
    {group name: figures} for one IPO, recomputed from the raw orders with the formulas above.
    figures["cell"][(category, tier)] = count / alloted / billing split by BUY (b) and SELL (s);
    plus the Premium, CALL / PUT, total and average figures a position row shows.
    """
    from collections import defaultdict
    pre, price = float(ipo.PreOpenPrice), float(ipo.IPOPrice)
    groups = defaultdict(lambda: {
        "cell": defaultdict(lambda: dict(cnt_b=0.0, cnt_s=0.0, al_b=0, al_s=0, bill_b=0.0, bill_s=0.0, sh_b=0.0, sh_s=0.0)),
        "prem": dict(q_b=0.0, q_s=0.0, a_b=0.0, a_s=0.0), "call_b": 0.0, "call_s": 0.0, "put_b": 0.0, "put_s": 0.0})
    for o in Order.objects.filter(user=user, OrderIPOName=ipo).select_related("OrderGroup"):
        g, side = groups[o.OrderGroup.GroupName], ("b" if o.OrderType == "BUY" else "s")
        if o.OrderCategory in ("Kostak", "Subject To"):
            g["cell"][(o.OrderCategory, o.InvestorType)][f"cnt_{side}"] += o.Quantity
        elif o.OrderCategory == "Premium":
            g["prem"][f"q_{side}"] += o.Quantity
            g["prem"][f"a_{side}"] += order_amount(o, ipo)
        elif o.OrderCategory in ("CALL", "PUT"):
            g[f"{o.OrderCategory.lower()}_{side}"] += order_amount(o, ipo)
    for od in OrderDetail.objects.filter(user=user, Order__OrderIPOName=ipo).select_related("Order__OrderGroup"):
        o = od.Order
        if o.OrderCategory not in ("Kostak", "Subject To"):
            continue
        c, side = groups[o.OrderGroup.GroupName]["cell"][(o.OrderCategory, o.InvestorType)], ("b" if o.OrderType == "BUY" else "s")
        c[f"bill_{side}"] += detail_amount(od, ipo)
        if od.AllotedQty not in (None, 0):
            c[f"al_{side}"] += 1
            c[f"sh_{side}"] += float(od.AllotedQty)
    for name, g in groups.items():
        cell = lambda cat, t: g["cell"][(cat, t)]
        g["k_shares"] = sum(cell("Kostak", t)["sh_b"] - cell("Kostak", t)["sh_s"] for t in TIERS)
        g["st_shares"] = sum(cell("Subject To", t)["sh_b"] - cell("Subject To", t)["sh_s"] for t in TIERS)
        g["k_bill"] = sum(cell("Kostak", t)["bill_b"] + cell("Kostak", t)["bill_s"] for t in TIERS)
        g["st_bill"] = sum(cell("Subject To", t)["bill_b"] + cell("Subject To", t)["bill_s"] for t in TIERS)
        g["p_shares"] = g["prem"]["q_b"] - g["prem"]["q_s"]
        g["p_bill"] = g["prem"]["a_b"] + g["prem"]["a_s"]
        g["call"], g["put"] = g["call_b"] + g["call_s"], g["put_b"] + g["put_s"]
        g["total_shares"] = g["k_shares"] + g["st_shares"] + g["p_shares"]
        g["total_amount"] = g["k_bill"] + g["st_bill"] + g["p_bill"] + g["call"] + g["put"]
        gain = pre - price
        g["total_avg"] = avg_text(g["total_amount"] / g["total_shares"] - gain) if g["total_shares"] else ""
    return dict(groups)
