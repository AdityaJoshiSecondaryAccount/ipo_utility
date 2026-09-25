"""Seed the selected remote IPO through Playwright UI and authenticated form views.

No ORM, database fixtures, local server, synthetic PANs or expected-value writes.
A persistent journal and a complete order multiset guard protect UI reruns.
"""
from collections import Counter
from datetime import datetime
import hashlib
import json
import logging
from pathlib import Path
import re
from playwright.sync_api import expect
from playwright_testing.remote import TARGET, RESULTS

LOG = logging.getLogger('billing-calculations')
FIELDS = {
    ('Kostak', 'RETAIL'): ('KostakQTY', 'KostakRate'),
    ('Kostak', 'SHNI'): ('KostakQTYSHNI', 'KostakRateSHNI'),
    ('Kostak', 'BHNI'): ('KostakQTYBHNI', 'KostakRateBHNI'),
    ('Subject To', 'RETAIL'): ('SubjectToQTY', 'SubjectToRate'),
    ('Subject To', 'SHNI'): ('SubjectToQTYSHNI', 'SubjectToRateSHNI'),
    ('Subject To', 'BHNI'): ('SubjectToQTYBHNI', 'SubjectToRateBHNI'),
    ('Premium', 'PREMIUM'): ('PremiumQTY', 'PremiumRate'),
    ('CALL', 'OPTIONS'): ('CallQTY', 'CallRate'),
    ('PUT', 'OPTIONS'): ('PutQTY', 'PutRate'),
}


class RemoteSeeder:
    def __init__(self, case, args):
        # Import the same pure parser utilities even when the verifier is __main__.
        from playwright_testing.calculation.verify_calculations import number, detail_upload_csv
        self.number, self.detail_csv = number, detail_upload_csv
        self.case, self.page, self.args = case, case.page, args
        self.ipo = str(case.ipo.pk)
        self.orders = sorted(case.orders, key=lambda row: row['side'])
        self.details = [d for d in case.details if d['category'] != 'Premium']
        account_key = hashlib.sha256(case.account[0].encode()).hexdigest()[:16]
        self.journal = RESULTS / 'seed-state' / f'{account_key}-{self.ipo}.json'
        self.fingerprint = hashlib.sha256(json.dumps([self.orders, self.details], default=str, sort_keys=True).encode()).hexdigest()
        self.state = dict(target=TARGET, ipo=self.ipo, fingerprint=self.fingerprint, phase='preflight', submitted=0)

    def save(self, **updates):
        self.state.update(updates)
        self.journal.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.journal.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.state, indent=2))
        temporary.replace(self.journal)

    def post(self, path, **kwargs):
        if not path.startswith('/') or path.startswith('//'):
            raise ValueError('Expected a path on the test site')
        token = next(c['value'] for c in self.page.context.cookies(TARGET) if c['name'] == 'csrftoken')
        response = self.page.request.post(TARGET + path,
            headers={'X-CSRFToken': token, 'Referer': TARGET + '/'},
            max_redirects=0, timeout=180000, **kwargs)
        if response.status not in (200, 302, 303):
            raise AssertionError(f'Seed request {path}: HTTP {response.status}; no automatic retry')
        if '/login' in response.headers.get('location', ''):
            raise AssertionError('Seed session expired; no automatic retry')
        return response

    def all_rows(self, path, selector, marker, table_selector="#example"):
        self.case.navigate(path)
        table = self.page.locator(table_selector)
        expect(table).to_be_attached()
        # Do not send page_size=All to an empty server paginator (page size zero).
        if table.locator(marker).count():
            dropdown = self.page.locator(selector)
            if dropdown.input_value() != 'All':
                with self.page.expect_navigation(wait_until='load'):
                    dropdown.select_option('All')
            expect(self.page.locator(selector)).to_have_value('All')
        return table

    def order_key(self, order):
        return (order['group'], order['side'], order['category'], order['investor'],
                self.number(order['qty']), self.number(order['rate']),
                order['method'] or 'Application',
                datetime.combine(order['date'], order['time']).isoformat())

    def order_snapshot(self):
        table = self.all_rows(f'/{self.ipo}/Order', '#Order_page_size', '.order-checkbox')
        rows = table.locator('tbody tr').filter(has=self.page.locator('.order-checkbox')).evaluate_all('''rows => rows.map(r => ({
            id:r.querySelector('.order-checkbox').value,
            cells:[...r.cells].map(c => c.textContent.trim())
        }))''')
        headers = table.locator('thead tr').first.locator('th').all_text_contents()
        labels = [' '.join(h.split()).lower() for h in headers]
        required = ['group name', 'order type', 'order category', 'premium strike price', 'investor type', 'qty', 'rate', 'date and time']
        indices = []
        for name in required:
            candidates = [i for i, h in enumerate(labels) if re.sub(r'[^a-z0-9]', '', h) == re.sub(r'[^a-z0-9]', '', name)]
            if len(candidates) != 1:
                raise AssertionError(f'Cannot read complete remote order table; missing/ambiguous {name}: {labels}')
            indices.append(candidates[0])
        result = Counter()
        for row in rows:
            group, side, cat, method, inv, qty, rate, stamp = [row['cells'][i] for i in indices]
            stamp = datetime.strptime(stamp, '%b. %d, %Y | %I:%M:%S %p').isoformat()
            if cat == 'Premium':
                method = 'Application'
            result[(group.strip().upper(), side, cat, inv, self.number(qty), self.number(rate), method, stamp)] += 1
        return result

    def validate_source(self):
        for side in ('BUY', 'SELL'):
            pans = [d['pan'] for d in self.details if d['side'] == side and d['pan']]
            if len(pans) != len(set(pans)):
                raise AssertionError(f'{side}: repeated source PANs cannot be imported faithfully by this application')
            if any(not re.fullmatch('[A-Z]{5}[0-9]{4}[A-Z]', pan) for pan in pans):
                raise AssertionError(f'{side}: invalid source PAN; refusing to invent substitute identities')
        if {d['preopen'] for d in self.case.details} != {self.number(221)}:
            raise AssertionError('This source requires a different pre-open-price setup')

    def prepare_groups(self):
        self.case.navigate('/group-billing-details/')
        existing = self.page.locator('#groupSelect option').all_text_contents()
        names = {x.strip().upper() for x in existing}
        for name in sorted({o['group'] for o in self.orders} - names):
            self.case.navigate('/GroupSetup')
            self.page.locator('[data-bs-target="#ADDGROUP"]').click()
            modal = self.page.locator('#ADDGROUP')
            modal.locator('[name="GroupName"]').fill(name)
            with self.page.expect_navigation(wait_until='load'):
                modal.get_by_role('button', name='Submit Form').click()
            LOG.info('Created source group: %s', name)
        self.case.navigate(f'/{self.ipo}/BUY')
        options = self.page.locator('#placeOrderForm [name="item_id"] option').evaluate_all('os => os.map(o => o.value)')
        missing = {o['group'] for o in self.orders} - set(options)
        if missing:
            raise AssertionError(f'Group creation rejected or group limit reached: {sorted(missing)}')

    def prepare_prices(self):
        self.case.navigate(f'/edit/{self.ipo}')
        expect(self.page.locator('[name="IPOType"]')).to_have_value('MAINBOARD')
        price = self.page.locator('[name="IPOPrice"]')
        if self.number(price.input_value()) != self.number(177):
            price.fill('177')
            with self.page.expect_navigation(wait_until='load'):
                self.page.locator('button[type="submit"]').click()
            self.case.navigate(f'/edit/{self.ipo}')
            if self.number(self.page.locator('[name="IPOPrice"]').input_value()) != self.number(177):
                raise AssertionError('IPO price update was rejected')
        self.post(f'/{self.ipo}/updatepreopenprice/All/All/All', form={'PreOpenPrice': '221'})

    def insert_order(self, order, index):
        side = order['side']
        if self.page.url.rstrip('/') != f'{TARGET}/{self.ipo}/{side}':
            self.case.navigate(f'/{self.ipo}/{side}')
        form = self.page.locator('#placeOrderForm')
        form.locator('[name="item_id"]').select_option(order['group'])
        # Clear every quantity/rate so a restored browser value cannot add extra orders.
        for qty, rate in FIELDS.values():
            form.locator(f'[name="{qty}"]').fill('')
            form.locator(f'[name="{rate}"]').fill('')
        stamp = datetime.combine(order['date'], order['time']).strftime('%Y-%m-%dT%H:%M:%S')
        form.locator('[name="datetime"]').evaluate('''(e,v) => {e.value=v;
            e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));}''', stamp)
        qty, rate = FIELDS[order['category'], order['investor']]
        form.locator(f'[name="{qty}"]').fill(str(order['qty']))
        form.locator(f'[name="{rate}"]').fill(str(order['rate']))
        if order['category'] == 'Subject To':
            suffix = {'RETAIL': 'Retail', 'SHNI': 'SHNI', 'BHNI': 'BHNI'}[order['investor']]
            form.locator('#subjectToIsPremium' + suffix).set_checked(order['method'] == 'Premium')
        if order['category'] in ('CALL', 'PUT'):
            form.locator(f'[name="{order["category"].title()}StrikePrice"]').fill(order['method'])
        self.save(phase='orders', pending_index=index)
        # The plain Place Order button does not send WhatsApp/email messages.
        with self.page.expect_response(lambda r: r.request.method == 'POST' and
                                       r.url.rstrip('/') == f'{TARGET}/{self.ipo}/{side}') as posted:
            with self.page.expect_navigation(wait_until='load'):
                self.page.locator('#btnPlaceOnly').click()
        response = posted.value
        if response.status != 200:
            raise AssertionError(f'Order {index + 1}: HTTP {response.status}; rerun will inspect server state before resuming')
        # Wait for the application's navigation, not just its success HTTP status.
        self.page.wait_for_load_state('load')
        self.save(submitted=index + 1, pending_index=None)
        LOG.info('Order submitted via %s UI: %s/%s (%s / %s / %s)', side, index + 1,
                 len(self.orders), order['group'], order['category'], order['investor'])

    def detail_snapshot(self, side):
        table = self.all_rows(f'/{self.ipo}/OrderDetail/{side}', '#page_size', 'input[name^="PAN_"]', '#sortable-table')
        rows = table.locator('input[name^="PAN_"]').evaluate_all('''inputs => inputs.map(p => {
            const r=p.closest('tr'), cells=[...r.cells].map(c=>c.textContent.trim());
            const qty=r.querySelector('input[name^="allotedqty_"]');
            return {id:p.id.replace('PAN_',''),pan:p.value,qty:qty?qty.value:null,cells};
        })''')
        result = []
        for row in rows:
            if row['qty'] is None:
                raise AssertionError('Broker allotment edit fields unavailable; account permissions required')
            c = row['cells']
            result.append(dict(id=row['id'], group=c[1].upper(), category=c[2], investor=c[3],
                rate=self.number(c[4]), side=side, pan=row['pan'].strip().upper(),
                allotted=None if row['qty'] == '' else self.number(row['qty'])))
        return result

    @staticmethod
    def detail_key(row):
        return tuple(row[k] for k in ('group', 'category', 'investor', 'side', 'rate', 'pan', 'allotted'))

    def import_details(self):
        self.save(phase='allotments')
        for side in ('BUY', 'SELL'):
            source = [d for d in self.details if d['side'] == side]
            present = self.detail_snapshot(side)
            if len(present) != len(source):
                raise AssertionError(f'{side}: expected {len(source)} application slots, got {len(present)}')
            # Valid PANs use the existing authenticated uploader; amounts are always computed by the app.
            nonempty = [d for d in source if d['pan']]
            if nonempty:
                self.post(f'/{self.ipo}/{side}/upload-csv/None/None/None/None/None',
                    multipart={'file': {'name': f'{side}-allotments.csv', 'mimeType': 'text/csv',
                                       'buffer': self.detail_csv(nonempty, side)}})
            present = self.detail_snapshot(side)
            blanks = [d for d in source if not d['pan']]
            unused = {r['id']: r for r in present if not r['pan']}
            for item in blanks:
                keys = ('group', 'category', 'investor', 'side', 'rate')
                matches = [r for r in unused.values() if all(r[k] == item[k] for k in keys)]
                if len(matches) != 1:
                    raise AssertionError(f'Blank-PAN allotment has {len(matches)} candidate rows; refusing ambiguous update')
                row = matches[0]
                unused.pop(row['id'])
                self.post(f'/{self.ipo}/{side}/update_pann/All/All/All',
                    form={f'allotedqty_{row["id"]}': '' if item['allotted'] is None else str(item['allotted'])})
            final = self.detail_snapshot(side)
            expected = Counter(self.detail_key(d) for d in source)
            actual = Counter(self.detail_key(d) for d in final)
            if actual != expected:
                raise AssertionError(f'{side} allotments rejected or mismatched: '
                    f'{sum((expected-actual).values())} missing, {sum((actual-expected).values())} unexpected. '
                    'No calculation pass will be reported. Inspect the remote upload validation messages.')
            LOG.info('Verified %s/%s %s application details, including blank PANs', len(final), len(source), side)

    def run(self):
        # Prevent concurrent menu runs from adding the same source twice.
        import fcntl
        self.journal.parent.mkdir(parents=True, exist_ok=True)
        with self.journal.with_suffix('.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise AssertionError('Another seed process is already using this IPO') from exc
            return self._run_locked()

    def _run_locked(self):
        self.validate_source()
        if self.journal.exists():
            previous = json.loads(self.journal.read_text())
            if any(previous.get(k) != self.state[k] for k in ('target', 'ipo', 'fingerprint')):
                raise AssertionError('Seed journal does not match this dataset; use a separate empty IPO')
            self.state = previous
        actual = self.order_snapshot()
        count = sum(actual.values())
        expected = Counter(self.order_key(o) for o in self.orders)
        if count and not self.journal.exists():
            raise AssertionError('IPO already contains orders without this seed journal. Use existing-data mode or an empty IPO; nothing was added.')
        if actual != Counter(self.order_key(o) for o in self.orders[:count]):
            raise AssertionError('Remote orders differ from the expected seeded prefix; refusing to append or delete data')
        self.save(submitted=count)
        self.prepare_groups()
        self.prepare_prices()
        for i in range(count, len(self.orders)):
            self.insert_order(self.orders[i], i)
            if (i + 1) % 25 == 0:
                if self.order_snapshot() != Counter(self.order_key(o) for o in self.orders[:i+1]):
                    raise AssertionError(f'Order completeness check failed at {i+1}; stopped without retrying submissions')
        if self.order_snapshot() != expected:
            raise AssertionError('Remote order multiset is not exactly the full source dataset')
        LOG.info('Verified all %s orders on the remote site; loading allotments', len(self.orders))
        self.import_details()
        # Recompute through the public price form after loading application details.
        self.post(f'/{self.ipo}/updatepreopenprice/All/All/All', form={'PreOpenPrice': '221'})
        self.save(phase='complete', orders_verified=len(self.orders), details_verified=len(self.details))
        LOG.info('Remote seed complete: %s orders, %s application rows. Starting calculation verification.',
                 len(self.orders), len(self.details))
