"""Regenerate route and template inventories from source, never from a database."""
import ast
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]


def discover():
    functions = {}
    for app in ('home',):
        tree = ast.parse((ROOT / app / 'views.py').read_text(encoding='utf-8-sig'))
        functions[app] = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    routes = []
    for app in functions:
        tree = ast.parse((ROOT / app / 'urls.py').read_text(encoding='utf-8-sig'))
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call) or not isinstance(n.func, ast.Name) or n.func.id != 'path':
                continue
            route, target = n.args[:2]
            if not isinstance(route, ast.Constant) or not isinstance(target, ast.Attribute):
                continue
            view = functions[app][target.attr]
            calls = [c for c in ast.walk(view) if isinstance(c, ast.Call)]
            templates = sorted({a.value for c in calls for a in c.args if isinstance(a, ast.Constant)
                                and isinstance(a.value, str) and a.value.endswith('.html')})
            params = {kind: sorted({c.args[0].value for c in calls if isinstance(c.func, ast.Attribute)
                and c.func.attr == 'get' and isinstance(c.func.value, ast.Attribute)
                and c.func.value.attr == kind and c.args and isinstance(c.args[0], ast.Constant)
                and isinstance(c.args[0].value, str)}) for kind in ('GET', 'POST')}
            decorators = [ast.unparse(d) for d in view.decorator_list]
            redirects = [ast.unparse(c.args[0]) for c in calls if isinstance(c.func, ast.Name)
                         and c.func.id == 'redirect' and c.args]
            routes.append(dict(app=app, route='/' + route.value,
                name=next((k.value.value for k in n.keywords if k.arg == 'name'), ''),
                namespace='', view=target.attr,
                line=view.lineno, decorators=decorators, templates=templates, parameters=params,
                redirects=redirects, methods='POST only' if 'require_POST' in decorators else
                'POST branch; other verbs not necessarily rejected' if params['POST'] else 'No method decorator',
                role='; '.join(decorators) or 'No explicit decorator; inspect view/session checks'))
    return routes


def write_inventory():
    routes = discover()
    out = ROOT / 'docs'
    out.mkdir(exist_ok=True)
    (out / 'playwright-routes.json').write_text(json.dumps(routes, indent=2), encoding='utf-8')
    text = ['# Application route inventory', '',
        'Source-derived route records; JSON includes parameters, redirects, templates, decorators and view line numbers.',
        'Decorators describe observed code, not a claim that access control is sufficient. No custom Django forms, DRF routers or viewsets were found.', '',
        '| App | Route | Name | View | Methods | Access | Templates |', '|---|---|---|---|---|---|---|']
    for r in routes:
        text.append('| ' + ' | '.join(str(v).replace('|', '\\|') for v in
            (r['app'], '`'+r['route']+'`', r['name'], r['view'], r['methods'], r['role'], ', '.join(r['templates']))) + ' |')
    (out / 'playwright-routes.md').write_text('\n'.join(text)+'\n', encoding='utf-8')
    interactions = []
    for path in sorted((ROOT / 'templates').rglob('*.html')):
        raw = path.read_text(encoding='utf-8-sig')
        clean = re.sub(r'{%\s*comment\s*%}.*?{%\s*endcomment\s*%}|<!--.*?-->', '', raw, flags=re.S)
        soup = BeautifulSoup(clean, 'html.parser')
        interactions.append(dict(template=str(path.relative_to(ROOT)),
            forms=[dict(action=f.get('action'), method=f.get('method'), fields=[dict(tag=x.name,
                **{k:x.get(k) for k in ('name','id','type','required','min','max','minlength','maxlength','pattern')})
                for x in f.select('input,select,textarea')]) for f in soup.select('form')],
            buttons=[dict(text=b.get_text(' ', strip=True), id=b.get('id'), onclick=b.get('onclick')) for b in soup.select('button')],
            links=[a.get('href') for a in soup.select('a[href]')],
            ajax=re.findall(r'(?:fetch|\$\.ajax)\s*\([^\n]{0,180}', clean)))
    (out / 'playwright-interactions.json').write_text(json.dumps(interactions, indent=2), encoding='utf-8')
    return routes


def write_resolved_inventory():
    from django.urls import get_resolver, URLResolver
    rows = []
    def walk(patterns, prefix='', namespace=''):
        for p in patterns:
            route = prefix + str(p.pattern)
            if isinstance(p, URLResolver):
                walk(p.url_patterns, route, ':'.join(filter(None, (namespace, p.namespace))))
            else:
                rows.append({'route': '/'+route, 'name': p.name, 'namespace': namespace,
                             'view': p.lookup_str})
    walk(get_resolver().url_patterns)
    (ROOT/'docs'/'playwright-resolved-routes.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    return rows


def write_coverage():
    routes = write_inventory()
    journeys = {
        'index':'home.test_e2e; e2e.tests.Workflows.test_login_refresh_logout_protects_deep_link',
        'indexforCustomer':'e2e.tests.Workflows.test_customer_cannot_access_broker_setup',
        'loginUser':'e2e.tests.Workflows.test_login_*',
        'logoutUser':'e2e.tests.Workflows.test_login_refresh_logout_protects_deep_link',
        'Changepassword':'e2e.pages_tests.Pages.test_password_mismatch_then_change_and_relogin',
        'AddClient':'home.test_e2e; e2e.tests.Workflows.test_client_edit_duplicate_and_filter',
        'AddIPO':'home.test_e2e.AddClientEndToEndTest.test_create_ipo_and_verify_all_home_card_pages',
        'AddGroup':'e2e.tests.Workflows.test_group_create_duplicate_edit_delete_cancel',
        'BulkUploadGroup':'e2e.tests.Workflows.test_group_bulk_csv_upload_and_sample_download',
        'DownloadGroupSample':'e2e.tests.Workflows.test_group_bulk_csv_upload_and_sample_download',
        'UpdateClient':'e2e.tests.Workflows.test_client_edit_duplicate_and_filter',
        'UpdateGroup':'e2e.tests.Workflows.test_group_create_duplicate_edit_delete_cancel',
        'DeleteGroup':'e2e.tests.Workflows.test_group_create_duplicate_edit_delete_cancel',
        'update':'e2e.pages_tests.Pages.test_ipo_edit_persists_price_and_name',
        'SetRate':'e2e.pages_tests.Pages.test_rates_save_and_reopen',
        'BUY':'home.test_e2e',
        'sell':'home.test_e2e.AddClientEndToEndTest.test_create_ipo_and_verify_all_home_card_pages',
        'dashboardform':'home.test_e2e.AddClientEndToEndTest.test_create_ipo_and_verify_all_home_card_pages',
        'user_profile':'e2e.tests.Workflows.test_profile_email_saved_and_password_visibility',
        'update_user_profile':'e2e.tests.Workflows.test_profile_email_saved_and_password_visibility',
        'accounting_view':'e2e.tests.Workflows.test_accounting_journal_payment_persists',
        'add_transaction':'e2e.tests.Workflows.test_accounting_journal_payment_persists',
        'soft_delete_accounting':'e2e.api_tests.Contracts.test_accounting_delete_reason_restore_and_audit',
        'restore_accounting':'e2e.api_tests.Contracts.test_accounting_delete_reason_restore_and_audit',
        'generate_shared_link':'e2e.api_tests.Contracts.test_shared_link_create_update_delete',
        'update_shared_link':'e2e.api_tests.Contracts.test_shared_link_create_update_delete',
        'delete_link':'e2e.api_tests.Contracts.test_shared_link_create_update_delete',
        'resolve_shared_link':'e2e.tests.Workflows.test_shared_link_*',
        'BulkDeleteClients':'e2e.api_tests.Contracts.test_bulk_deletes_preserve_referenced_clients_groups_and_foreign_data',
        'BulkDeleteGroup':'e2e.api_tests.Contracts.test_bulk_deletes_preserve_referenced_clients_groups_and_foreign_data',
        'BulkDeleteOrders':'e2e.api_tests.Contracts.test_bulk_deletes_preserve_referenced_clients_groups_and_foreign_data',
        'AddPan':'e2e.api_tests.Contracts.test_pan_validation_update_clear_and_billing_calculation',
        'updatepreopenprice':'e2e.api_tests.Contracts.test_pan_validation_update_clear_and_billing_calculation',
        'bulk_ipo_transactions':'e2e.api_tests.Contracts.test_bulk_payment_is_atomic_on_invalid_total',
        'UpdateOrder':'e2e.api_tests.Contracts.test_order_update_changes_rate_and_quantity',
    }
    pages = {'IPOSETUP','ClientSetup','GroupSetup','edit','EditClient','EditGroup','EditOrder','dashboard',
             'OrderFunction','OrderDetailFunction','Billing','Status','GroupWiseDashboard','group_billing_details',
             'BackUp','accounting_logs_view'}
    text=['# Playwright coverage matrix','',
        'TESTED means an executable check exists, not that it passed or that every branch is covered.',
        'Anonymous-only checks do not establish authenticated workflow coverage. See the JSON interaction inventory for individual fields/buttons and the final report for failures.', '',
        '| App | Page/view | URL name | Route | Role | Feature | Scenario | Priority | Test file | Status |',
        '|---|---|---|---|---|---|---|---|---|---|']
    for i,r in enumerate(routes):
        view=r['view']; files=journeys.get(view,'')
        if files:
            scenario='Workflow and persistence/validation as named; route aliases share view logic'
        elif view in pages:
            files='e2e.pages_tests.Pages; home.test_e2e'
            scenario='Content, deep link, refresh and form checks; not all table actions'
        else:
            scenario='Anonymous response contract only; authenticated mutation/export/provider behavior not covered'
        if view not in {'loginUser','logoutUser','resolve_shared_link'}:
            files += f'; e2e.api_tests.AnonymousRoutes.test_{i:03d}_{view}'
        text.append('| '+' | '.join(str(x).replace('|','\\|') for x in
            [r['app'],view,r['name'],'`'+r['route']+'`',r['role'],'; '.join(r['templates']) or 'Action/API',
             scenario,'P0' if view in journeys else 'P1',files.strip('; '),'TESTED'])+' |')
    text += ['', '## Explicit limits', '',
        '- Every application route declaration is represented, including aliases and the duplicate send-status route. Route-level coverage is not exhaustive functional coverage.',
        '- Live registrar CAPTCHA/allotment, Telegram OTP/session and email delivery are intentionally excluded from real providers. This application has no active WhatsApp routes; WhatsApp-specific tests from the source suite are excluded.',
        '- Complex bulk transfers, every export format, every upload parser, every table filter/sort/page-size combination, and all order-category boundary combinations remain functional coverage gaps.',
        '- Framework admin routes: representative group CRUD and broker denial are tested; individual field validation for every registered model is intentionally excluded. PWA manifest/service-worker routes are NOT USER-FACING framework resources.',
        '- Static legacy templates not referenced by any active view are NOT USER-FACING; the interaction JSON retains them for review.',
        '- No password-reset email/token routes, DRF router/viewset endpoints, or custom forms.py were discovered.',
        '- Browser engine coverage is Chromium only; Firefox/WebKit are intentionally excluded until application regressions are fixed.',
        '- Prefix/root/framework routes are expanded separately in playwright-resolved-routes.json.']
    (ROOT/'docs'/'playwright-coverage.md').write_text('\n'.join(text)+'\n',encoding='utf-8')


def append_framework_coverage(rows):
    lines=['', '## Framework route accounting', '',
           '| Route | Name | View | Status | Reason/test |', '|---|---|---|---|---|']
    for row in rows:
        if row['namespace'] != 'admin' and not row['view'].startswith('pwa.'):
            continue
        if row['view'].startswith('pwa.'):
            status='NOT USER-FACING'; reason='Manifest/service worker/offline framework resource; excluded from business workflows'
        elif (row['name'] or '') in ('login','index','home_groupdetail_add','home_groupdetail_change','home_groupdetail_delete','home_groupdetail_changelist'):
            status='TESTED'; reason='e2e.pages_tests.Pages.test_admin_broker_denied_and_superuser_crud'
        else:
            status='INTENTIONALLY EXCLUDED'; reason='Framework admin surface; representative group CRUD covered, per-model admin validation not implemented'
        lines.append('| '+' | '.join(str(v).replace('|','\\|') for v in
            (row['route'],row['name'],row['view'],status,reason))+' |')
    with (ROOT/'docs'/'playwright-coverage.md').open('a',encoding='utf-8') as out:
        out.write('\n'.join(lines)+'\n')


if __name__ == '__main__':
    print(f'Inventoried {len(write_inventory())} application route declarations.')
