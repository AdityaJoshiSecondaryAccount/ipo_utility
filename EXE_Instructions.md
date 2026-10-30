# EXE Build and Maintenance Instructions

**CRITICAL NOTE FOR DEVELOPERS:**

Whenever core files are replaced, updated, or rewritten from a previous backup, you **must** ensure that the following code snippets are properly re-inserted to prevent the application or backups from failing.

---

## 1. Database Backup Trigger (`home/views.py`)

If `home/views.py` is replaced, the automated background database backups will fail to execute unless you restore this code.

**Step 1: Add the Import Statement**
At the top of the `home/views.py` file (alongside the other module imports), include:
```python
from .db_backup import trigger_background_db_upload
```

**Step 2: Trigger the Backup in `IPO_Allotment`**
Inside the `IPO_Allotment` function definition, call the trigger immediately after the `POST` and authentication checks:
```python
def IPO_Allotment(request,IPOid,OrderType,group=None,IPOType=None,InvestType=None,Rate='All'):
    if request.method == "POST":
        if request.user and request.user.is_authenticated:
            trigger_background_db_upload(request.user.username) # <--- THIS LINE IS REQUIRED
        
        ipo_register =  request.POST.get('ipo_register', '')
        # ... rest of the function ...
```

---

## 2. Expiry Date Default Logic (`home/models.py`)

If `home/models.py` is replaced, the `.exe` compilation and database migrations will crash if the callable default for `Expiry_Date` is missing.

**Step 1: Define the callable function**
Just above the `CustomUser` class in `home/models.py`, add this function:
```python
def get_default_expiry_date():
    return (now() + timedelta(days=365)).date()
```

**Step 2: Use the callable in `CustomUser`**
Ensure the `Expiry_Date` field uses this function as its default (without calling it with parentheses):
```python
class CustomUser(AbstractUser):
    # ...
    Expiry_Date = models.DateField(default=get_default_expiry_date) # <--- USE THE FUNCTION NAME HERE
```
*Note: Do NOT use `default=now() + timedelta(days=365)`. This will cause the date to be static based on server boot time, and it will break migrations.*

---

## 3. PWA Tags & Banner Removal (`templates/basic.html`)

If `templates/basic.html` is ever replaced with an older web-based version, you will encounter a `TemplateSyntaxError` for `'pwa'`. Because the application is now a desktop `.exe`, PWA functionality is unsupported and unneeded.

**Step 1: Remove Template Tags**
Delete these two lines from the very top of `basic.html`:
```html
{% load pwa %}
{% progressive_web_app_meta %}
```

**Step 2: Remove the PWA Install Banner**
Search for and completely delete the HTML and JavaScript block labeled `<!-- ======= PWA INSTALL BANNER ======= -->` at the bottom of the file to prevent the useless "Install on iPhone/Android" banner from appearing inside the `.exe`.

---

## 4. Fix Accounting View TypeError (`home/views.py`)

If `home/views.py` is restored from an older backup, visiting `/accounting/` will cause a `TypeError: args or kwargs must be provided`. This happens because Django 6.0 strictly requires arguments when using `format_html`.

**The Fix:**
First, ensure you import `mark_safe` at the top of the file:
```python
from django.utils.safestring import mark_safe
```
Then, you must replace `format_html` with `mark_safe` when passing a pre-formatted string.

Find these two lines inside the `accounting_view` and `accounting_logs` functions:
```python
"html_table": format_html(html_table),
"audit_log_html": format_html(audit_log_html),
```
Change them to:
```python
"html_table": mark_safe(html_table),
"audit_log_html": mark_safe(audit_log_html),
```

---

## 5. Fix Regex SyntaxWarning (`home/views.py`)

If `home/views.py` is restored from an older backup, Python 3.12+ will throw a `SyntaxWarning` for invalid escape sequences in regular expressions.

**The Fix:**
Find the `isValidPAN` function in `home/views.py`:
```python
def isValidPAN(Z): 
    Result=re.compile("[A-Za-z]{5}\d{4}[A-Za-z]{1}") 
    return Result.match(Z) 
```
Change the regex string to a raw string by prefixing it with `r`:
```python
def isValidPAN(Z): 
    Result=re.compile(r"[A-Za-z]{5}\d{4}[A-Za-z]{1}") 
    return Result.match(Z) 
```

---

## 6. Hide "Manage Links" Button (`templates/OrderDetail.html` & `templates/OrderDetail - Sell.html`)

In the standalone `.exe` version, the "Manage Links" functionality is not supported. You must ensure the button is hidden from users while keeping the underlying logic intact to avoid breaking the frontend.

**The Fix:**
In both `templates/OrderDetail.html` and `templates/OrderDetail - Sell.html`, search for `Manage Links` to find the corresponding `<button>` elements (they usually appear multiple times in each file). 

Add `style="display: none;"` directly into the button tag:
```html
<!-- Example of modified button -->
<button class="btn btn-secondary" style="display: none;"
        data-toggle="modal" 
        data-target="#linkManagementModal" 
        onclick="loadUserLinks()"
        data-dismiss="modal">
    Manage Links
</button>
```
Make sure you update every instance of this button in both files!
