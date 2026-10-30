# Summary of Changes for Orders Status Modal AVG Toggle

This document records the exact modifications made across the codebase to implement the **AVG toggle (Average by Application vs. Average by Premium)** in the Orders Status modal (`#exampleModal`).

---

## 1. Modified Files List
1. `home/views.py` (and mirrored copy in `uploads/home/views.py`)
2. `templates/Order.html` (and mirrored copy in `uploads/templates/Order.html`)

---

## 2. Details of Changes in `home/views.py`

### Location:
Inside `def filterfromstatus(...)` / `def Order(...)` view around lines 6063–6120:

### Logic Added:
1. **Per-Category / Investor Calculation (`dict_avg`)**:
   - Calculated `AvgApp` = `total_amount / total_count`
   - Calculated `AvgPrem` = `AvgApp / LotSize` (`IPO.LotSizeRetail`, `IPO.LotSizeSHNI`, `IPO.LotSizeBHNI`) for `SubjectTo` orders.
   - Populated `dict_avg[f"{dict_key_prefix}AvgApp"]` and `dict_avg[f"{dict_key_prefix}AvgPrem"]`.
2. **Net Row Calculation (`net_avg`)**:
   - Added `net_avg[f"{key_prefix}AvgApp"] = round(net_a, 2)`
   - Added `net_avg[f"{key_prefix}AvgPrem"] = round(net_a / inv_lot, 2)` for `SubjectTo`.

```diff
--- a/home/views.py
+++ b/home/views.py
@@ -6063,7 +6063,21 @@ def filterfromstatus(request, IPOid, Groupfilter, OrderCategoryFilter, InvestorT
 
                 # Save into dicts
                 dict_count[f"{dict_key_prefix}Count"] = total_count
-                dict_avg[f"{dict_key_prefix}Avg"] = (total_amount / total_count) if total_count else 0
+                avg_val = (total_amount / total_count) if total_count else 0
+                dict_avg[f"{dict_key_prefix}Avg"] = avg_val
+
+                # Calculate per-premium avg if category is Subject To
+                if ordercategory == "SubjectTo":
+                    if investortype == "RETAIL":
+                        inv_lot = IPO.LotSizeRetail or 1
+                    elif investortype == "SHNI":
+                        inv_lot = IPO.LotSizeSHNI or 1
+                    elif investortype == "BHNI":
+                        inv_lot = IPO.LotSizeBHNI or 1
+                    else:
+                        inv_lot = 1
+                    dict_avg[f"{dict_key_prefix}AvgApp"] = avg_val
+                    dict_avg[f"{dict_key_prefix}AvgPrem"] = (avg_val / inv_lot) if inv_lot else 0
                 dict_amount[f"{dict_key_prefix}Amount"] = total_amount
     net_count = {}
     net_avg = {}
@@ -6101,6 +6115,17 @@ def filterfromstatus(request, IPOid, Groupfilter, OrderCategoryFilter, InvestorT
             key_prefix = f"{ordercategory}{investortype}Net"
             net_count[f"{key_prefix}Count"] = net_c
             net_avg[f"{key_prefix}Avg"] = round(net_a, 2)
+            if ordercategory == "SubjectTo":
+                if investortype == "RETAIL":
+                    inv_lot = IPO.LotSizeRetail or 1
+                elif investortype == "SHNI":
+                    inv_lot = IPO.LotSizeSHNI or 1
+                elif investortype == "BHNI":
+                    inv_lot = IPO.LotSizeBHNI or 1
+                else:
+                    inv_lot = 1
+                net_avg[f"{key_prefix}AvgApp"] = round(net_a, 2)
+                net_avg[f"{key_prefix}AvgPrem"] = round((net_a / inv_lot) if inv_lot else 0, 2)
             net_amount[f"{key_prefix}Amount"] = round(net_amt, 2)
```

---

## 3. Details of Changes in `templates/Order.html`

### A. Mainboard Subject To Table Header (`<th colspan="10">`)
Added pill switch `[App Avg | Prem Avg]` in the Subject To header, added `subject-to-avg-header` class to the AVG columns:
```html
<th colspan="10" style="border: 1px solid black; border-collapse: collapse;">
    <div style="display: flex; align-items: center; justify-content: center; position: relative;">
        <span>Subject To</span>
        <div class="btn-group btn-group-toggle subject-to-avg-toggle" data-toggle="buttons" style="position: absolute; right: 8px; font-size: 11px;">
            <label class="btn btn-outline-primary btn-xs active px-2 py-0" style="font-size: 11px; line-height: 1.5; cursor: pointer;" title="Show Average per Application Form">
                <input type="radio" name="subjectToAvgMode" value="app" autocomplete="off" checked onchange="switchSubjectToAvgMode('app')"> App Avg
            </label>
            <label class="btn btn-outline-primary btn-xs px-2 py-0" style="font-size: 11px; line-height: 1.5; cursor: pointer;" title="Show Average per Share (Premium)">
                <input type="radio" name="subjectToAvgMode" value="prem" autocomplete="off" onchange="switchSubjectToAvgMode('prem')"> Prem Avg
            </label>
        </div>
    </div>
</th>
```

### B. Mainboard & SME Subject To AVG Cells
Added `class="status-avg-cell"`, `data-avg-app="..."`, and `data-avg-prem="..."`:
```html
<td style="border: 1px solid black; border-collapse: collapse;" 
    class="status-avg-cell" 
    data-avg-app="{{dict_avg.SubjectToRETAILBUYAvgApp|default:dict_avg.SubjectToRETAILBUYAvg|default_if_none:''|floatformat:2}}" 
    data-avg-prem="{{dict_avg.SubjectToRETAILBUYAvgPrem|default_if_none:''|floatformat:2}}" 
    data-status-value="{{dict_avg.SubjectToRETAILBUYAvg|default_if_none:''}}">
    {{dict_avg.SubjectToRETAILBUYAvg|floatformat:2}}
</td>
```
(Repeated for Retail, SHNI, BHNI across BUY, SELL, NET rows, and for SME table).

### C. JavaScript Function `switchSubjectToAvgMode(mode)`
Added helper function and initialization:
```javascript
function switchSubjectToAvgMode(mode) {
    if (!mode) mode = 'app';
    try {
        localStorage.setItem('subjectToAvgMode', mode);
    } catch (e) {}

    document.querySelectorAll('.subject-to-avg-toggle input[type="radio"]').forEach(radio => {
        const isMatch = (radio.value === mode);
        radio.checked = isMatch;
        const label = radio.closest('label');
        if (label) {
            if (isMatch) label.classList.add('active');
            else label.classList.remove('active');
        }
    });

    const headerText = mode === 'prem' ? 'AVG (Prem)' : 'AVG (App)';
    document.querySelectorAll('.subject-to-avg-header').forEach(th => {
        th.textContent = headerText;
    });

    document.querySelectorAll('.subjectto-table .status-avg-cell').forEach(cell => {
        const val = mode === 'prem' ? cell.dataset.avgPrem : cell.dataset.avgApp;
        const cleanVal = (val !== undefined && val !== null) ? String(val).trim() : '';
        cell.textContent = cleanVal || '0.00';
        cell.dataset.statusValue = cleanVal;
    });
}
```

---

## 4. How to Revert

If you want to revert these changes completely using git:
```bash
git checkout -- home/views.py templates/Order.html
cp home/views.py uploads/home/views.py
cp templates/Order.html uploads/templates/Order.html
```
