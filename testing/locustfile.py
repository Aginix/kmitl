"""Locust load test for the KMITL Odoo 16 ERP.

Simulates a staff member logging in (credentials from users.csv), then
browsing Discuss, Todo, purchase requests, the budget-approval flow
(agx_approval: create -> submit for verification -> reserve budget), and
procurement/budget records.
"""

import csv
import functools
import itertools
import os
import threading

from locust import HttpUser, task, constant

# Set the real target via env var or --host at run time — do not hardcode a
# real server/db name here, this file is committed to the repo. e.g.:
#   ODOO_DB=<db_name> locust -f testing/locustfile.py --host=https://<your-odoo-host>
ODOO_URL = os.environ.get("ODOO_URL", "http://localhost:16069")
ODOO_DB = os.environ.get("ODOO_DB")
ODOO_VERIFY_SSL = os.environ.get("ODOO_VERIFY_SSL", "1") not in ("0", "false", "False")

USERS_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.csv")


def _load_credentials():
    with open(USERS_CSV, newline="", encoding="utf-8") as f:
        return [
            (row["Email"], row["Password"])
            for row in csv.DictReader(f)
            if row.get("Email") and row.get("Password")
        ]


_CREDENTIALS = _load_credentials()
_credentials_cycle = itertools.cycle(_CREDENTIALS)
_credentials_lock = threading.Lock()


def _next_credentials():
    with _credentials_lock:
        return next(_credentials_cycle)


def _requires_login(fn):
    """Skip the task entirely if on_start's login never succeeded — running
    tasks against an unauthenticated session just piles up doomed requests."""

    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        if not self.uid:
            return
        return fn(self, *args, **kwargs)

    return wrapper


# Budget account + 4 analytic dimensions — given explicitly (คณะครุศาสตร์
# อุตสาหกรรมและเทคโนโลยี / OU ครุศาสตร์), not mined: the budget engine only
# matches when all dimensions line up exactly, so these must be a real,
# already-appropriated combination.
BUDGET_ACCOUNT_ID = 152  # [5103010000] งบดำเนินงาน / ค่าใช้สอย / ค่าใช้จ่ายเดินทางเพื่องานราชการในประเทศ
DEPARTMENT_ANALYTIC_ID = 474  # [03000] คณะครุศาสตร์อุตสาหกรรมและเทคโนโลยี
ACTIVITY_ANALYTIC_ID = 264  # [09007010110] กิจกรรมรอง กิจกรรมบริหารทั่วไป
FUND_ANALYTIC_ID = 249  # [0100] กองทุนทั่วไป
SOURCE_ANALYTIC_ID = 421  # [2] งบประมาณเงินรายได้
TOTAL_AMOUNT = 100.0

# Fixed approval.request fields — chosen explicitly rather than mined, since
# category 1 requires a period + city and its participants are given directly.
CATEGORY_ID = 1
CITY = "ทดสอบ"
DATE_START = "2026-08-01"
DATE_END = "2026-08-31"
PARTICIPANT_PARTNER_IDS = [22714, 5120]
LINE_PRODUCT_IDS = [125, 126, 127, 128]  # ค่าเดินทาง / ค่าเบี้ยเลี้ยง / ค่าที่พัก / ค่าใช้จ่ายอื่น ๆ

# Auto-detected database name (when ODOO_DB isn't set), shared by every user.
_db_lock = threading.Lock()
_db_cache = {}


class KMITLUser(HttpUser):
    wait_time = constant(2)
    host = ODOO_URL

    def on_start(self):
        self.uid = None
        self.client.verify = ODOO_VERIFY_SSL
        self.email, self.password = _next_credentials()
        self._login()

    # ── Plumbing ───────────────────────────────────────────────────────────

    def _resolve_db(self):
        if _db_cache.get("name"):
            return _db_cache["name"]
        with _db_lock:
            if _db_cache.get("name"):
                return _db_cache["name"]
            name = ODOO_DB
            if not name:
                dbs = self._json_route("/web/database/list", name="[Init] List databases") or []
                if len(dbs) == 1:
                    name = dbs[0]
                elif len(dbs) > 1:
                    print(f"[Init] Multiple databases found ({dbs}) — set ODOO_DB explicitly")
            if name:
                _db_cache["name"] = name
            return name

    def _login(self):
        db = self._resolve_db()
        if not db:
            return  # already recorded as a failure by _resolve_db's own request
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "db": db,
                "login": self.email,
                "password": self.password,
            },
        }
        with self.client.post(
            "/web/session/authenticate",
            json=payload,
            catch_response=True,
            name="[Auth] Login",
        ) as resp:
            result = (resp.json() or {}).get("result") or {}
            if not result.get("uid"):
                resp.failure(f"Login failed for {self.email}")
            else:
                self.uid = result["uid"]

    @staticmethod
    def _error_message(data):
        error = (data or {}).get("error") or {}
        return error.get("data", {}).get("message") or error.get("message") or "RPC error"

    def _rpc(self, model, method, args=None, kwargs=None, name=None):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": method,
                "args": args or [],
                "kwargs": kwargs or {},
            },
        }
        label = name or f"[RPC] {model}.{method}"
        with self.client.post(
            "/web/dataset/call_kw", json=payload, catch_response=True, name=label
        ) as resp:
            try:
                data = resp.json()
            except Exception as e:
                resp.failure(f"JSON decode error: {e}")
                return None
            if not data or "error" in data:
                resp.failure(self._error_message(data))
                return None
            return data.get("result")

    def _json_route(self, path, params=None, name=None):
        payload = {"jsonrpc": "2.0", "method": "call", "params": params or {}}
        with self.client.post(
            path, json=payload, catch_response=True, name=name or f"[JSON] {path}"
        ) as resp:
            try:
                data = resp.json()
            except Exception as e:
                resp.failure(f"JSON decode error: {e}")
                return None
            if not data or "error" in data:
                resp.failure(self._error_message(data))
                return None
            return data.get("result")

    # ── Tasks ──────────────────────────────────────────────────────────────

    @task(3)
    @_requires_login
    def open_discuss(self):
        self._json_route("/mail/init_messaging", name="[Discuss] Open")

    @task(3)
    @_requires_login
    def open_todo(self):
        self._rpc(
            model="mail.activity",
            method="search_read",
            args=[[["is_my_todo", "=", True]]],
            kwargs={
                "fields": [
                    "state",
                    "todo_category",
                    "summary",
                    "res_name",
                    "res_model_id",
                    "user_id",
                    "date_deadline",
                    "is_read_by_me",
                ],
                "limit": 20,
            },
            name="[Todo] Browse my todos",
        )

    @task(3)
    @_requires_login
    def open_purchase_request(self):
        self._rpc(
            model="purchase.request",
            method="search_read",
            args=[[]],
            kwargs={
                "fields": [
                    "name",
                    "state",
                    "requested_by",
                    "assigned_to",
                    "date_start",
                    "estimated_cost",
                    "line_count",
                ],
                "limit": 20,
            },
            name="[Purchase Request] Browse",
        )

    @task(4)
    @_requires_login
    def agx_approval_flow(self):
        self._rpc(
            model="approval.request",
            method="search_read",
            args=[[]],
            kwargs={
                "fields": ["name", "state", "category_id", "owner_id", "total_actual_amount"],
                "limit": 20,
            },
            name="[Approval] Browse list",
        )

        line_amount = TOTAL_AMOUNT / len(LINE_PRODUCT_IDS)
        request_id = self._rpc(
            model="approval.request",
            method="create",
            args=[
                {
                    "category_id": CATEGORY_ID,
                    "description": "Locust load test request",
                    "city": CITY,
                    "date_start": DATE_START,
                    "date_end": DATE_END,
                    "budget_account_id": BUDGET_ACCOUNT_ID,
                    "department_analytic_id": DEPARTMENT_ANALYTIC_ID,
                    "source_analytic_id": SOURCE_ANALYTIC_ID,
                    "fund_analytic_id": FUND_ANALYTIC_ID,
                    "activity_analytic_id": ACTIVITY_ANALYTIC_ID,
                    "participant_ids": [
                        (0, 0, {"partner_id": partner_id}) for partner_id in PARTICIPANT_PARTNER_IDS
                    ],
                    "line_ids": [
                        (0, 0, {"product_id": product_id, "total_amount": line_amount})
                        for product_id in LINE_PRODUCT_IDS
                    ],
                }
            ],
            name="[Approval] Create request",
        )
        if not request_id:
            return

        self._rpc(
            model="approval.request",
            method="read",
            args=[[request_id]],
            kwargs={"fields": ["name", "state", "category_id", "budget_account_id", "line_ids"]},
            name="[Approval] Read request",
        )

        self._rpc(
            model="approval.request",
            method="action_to_verify",
            args=[[request_id]],
            name="[Approval] Submit for verification",
        )

        self._rpc(
            model="approval.request",
            method="action_reserve_budget",
            args=[[request_id]],
            name="[Approval] Reserve budget",
        )

    @task(2)
    @_requires_login
    def browse_procurement_plan(self):
        self._rpc(
            model="procurement.plan",
            method="search_read",
            args=[[]],
            kwargs={
                "fields": ["name", "description", "state", "total_price", "user_id"],
                "limit": 20,
            },
            name="[Procurement Plan] Browse",
        )

    @task(2)
    @_requires_login
    def browse_budget_move(self):
        self._rpc(
            model="budget.move",
            method="search_read",
            args=[[]],
            kwargs={
                "fields": ["name", "ref", "state", "budget_type", "total_amount", "move_type"],
                "limit": 20,
            },
            name="[Budget Move] Browse",
        )

    @task(2)
    @_requires_login
    def browse_budget_commitment(self):
        self._rpc(
            model="budget.commitment",
            method="search_read",
            args=[[]],
            kwargs={
                "fields": ["name", "title", "state", "amount", "account_id", "available_to_obligate"],
                "limit": 20,
            },
            name="[Budget Commitment] Browse",
        )
