"""Post-init demo data for the KMITL post-budget finance flow.

Three demo stories run in order from ``seed``:

* the disbursement flow (``PR -> PA -> PO -> Work Acceptance -> DR``), moved here
  from ``kmitl_demo``;
* vendor bills created and posted from those DRs, leaving every request at
  ``bills_posted``;
* fixed assets with posted depreciation.

The demo deliberately stops at ``bills_posted``: the payment tail (audit ->
authorize -> pay) is left untouched so the finance queue can be exercised by
hand in the UI, and no ``account.payment`` is created here.

The disbursement flow reuses two helpers from ``kmitl_demo`` (the purchase
end-to-end flow uses them too) instead of duplicating them.
"""

import logging

from odoo import SUPERUSER_ID, api, fields
from odoo.fields import Command

from odoo.addons.kmitl_demo.hooks import (
    _create_budget_appropriation,
    _run_non_egp_flow,
)

_logger = logging.getLogger(__name__)


def post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    seed(env)


def seed(env, disbursement=True, assets=True):
    """Build the demo stories on an existing environment.

    Split out of ``post_init`` so the dev-only regenerate wizard and module
    installation share one code path. Each story is independent.
    """
    if disbursement:
        drs = _create_disbursement_flow_demo(
            env,
            admin=env.ref("base.user_admin"),
            fiscal_year=env.ref("kmitl_demo.account_fiscal_year_y2568"),
            admin_employee=_admin_employee(env),
            supervisor_employee=env.ref("kmitl_demo.employee_demo_008"),
            wa_committee_employees=_wa_committee_employees(env),
        )
        _create_bill_demo(env, drs)
    if assets:
        _create_asset_demo(env)


def _admin_employee(env):
    """The hr.employee linked to the admin user (work-acceptance chairman)."""
    admin = env.ref("base.user_admin")
    return env["hr.employee"].search([("user_id", "=", admin.id)], limit=1)


def _wa_committee_employees(env):
    """Work-acceptance committee members shared across the demo flows."""
    return (
        env.ref("kmitl_demo.employee_demo_012")
        + env.ref("kmitl_demo.employee_demo_011")
        + env.ref("kmitl_demo.employee_demo_020")
        + env.ref("kmitl_demo.employee_demo_018")
    )


# === Disbursement-flow demo (PR → PA → PO → WA → DR) ===
#
# 10 PRs in FY 2568, each with a different (budget_account, fund, source,
# activity) combination. Case #1 mirrors the reference memo อว 7001.14/14309
# (สำนักงานพัสดุ, ค่าโปรแกรมคอมพิวเตอร์). Amounts are kept ≤ 100,000 ฿ so
# is_egp stays False and every case follows the non-EGP PA chain through to
# disbursement-request creation.

DR_CASES = [
    # Case 1 — image reference (ค่าโปรแกรมคอมพิวเตอร์, สำนักงานพัสดุ)
    {
        "title": "[E2E-DR] จัดซื้อโปรแกรมคอมพิวเตอร์ (อิงตามภาพ อว 7001.14/14309)",
        "description": (
            "บันทึกข้อความ อว 7001.14/14309 ลว. 4 ธ.ค. 2567 — "
            "ขออนุมัติเบิกค่าโปรแกรมคอมพิวเตอร์ ปีงบประมาณ 2568 "
            "(จำนวนเงินตัวอย่างปรับลงเพื่อเลี่ยง e-GP threshold)"
        ),
        "price_unit": 95_000,
        "vendor": "kmitl_demo.vendor_demo_002",
        "budget_account": "budget.budget_account_5414000001",
        "fund": "account_analytic_kmitl.fund_0600",
        "source": "account_analytic_kmitl.source_1",
        "activity": "account_analytic_kmitl.activity_09007",
        "dept": "account_analytic_kmitl.dept_89390",
        "department": "kmitl_demo.89390",
        "operating_unit": "operating_unit_kmitl.operating_unit_89",
        "proc_type": "purchase_request_kmitl.procurement_type_004",
        "payment_type": "direct",
    },
    {
        "title": "[E2E-DR] จัดซื้อวัสดุสำนักงาน",
        "description": "วัสดุสำนักงานสำหรับการดำเนินงานทั่วไป",
        "price_unit": 25_000,
        "vendor": "kmitl_demo.vendor_demo_004",
        "budget_account": "budget.budget_account_5104010101",
        "fund": "account_analytic_kmitl.fund_0200",
        "source": "account_analytic_kmitl.source_2",
        "activity": "account_analytic_kmitl.activity_06",
        "dept": "account_analytic_kmitl.dept_01",
        "department": "kmitl_demo.01",
        "operating_unit": "operating_unit_kmitl.operating_unit_01",
        "proc_type": "purchase_request_kmitl.procurement_type_004",
        "payment_type": "direct",
    },
    {
        "title": "[E2E-DR] จัดซื้อวัสดุคอมพิวเตอร์",
        "description": "วัสดุคอมพิวเตอร์และอิเล็กทรอนิกส์",
        "price_unit": 18_000,
        "vendor": "kmitl_demo.vendor_demo_002",
        "budget_account": "budget.budget_account_5104010109",
        "fund": "account_analytic_kmitl.fund_0100",
        "source": "account_analytic_kmitl.source_1",
        "activity": "account_analytic_kmitl.activity_09",
        "dept": "account_analytic_kmitl.dept_01",
        "department": "kmitl_demo.01",
        "operating_unit": "operating_unit_kmitl.operating_unit_01",
        "proc_type": "purchase_request_kmitl.procurement_type_004",
        "payment_type": "direct",
    },
    {
        "title": "[E2E-DR] จัดซื้อวัสดุวิทยาศาสตร์",
        "description": "วัสดุวิทยาศาสตร์สำหรับห้องปฏิบัติการ",
        "price_unit": 32_000,
        "vendor": "kmitl_demo.vendor_demo_008",
        "budget_account": "budget.budget_account_5104010115",
        "fund": "account_analytic_kmitl.fund_0100",
        "source": "account_analytic_kmitl.source_1",
        "activity": "account_analytic_kmitl.activity_09",
        "dept": "account_analytic_kmitl.dept_01",
        "department": "kmitl_demo.01",
        "operating_unit": "operating_unit_kmitl.operating_unit_01",
        "proc_type": "purchase_request_kmitl.procurement_type_004",
        "payment_type": "prepaid",
    },
    {
        "title": "[E2E-DR] เช่าทรัพย์สิน (เครื่องถ่ายเอกสาร)",
        "description": "เช่าเครื่องถ่ายเอกสารประจำสำนักงาน",
        "price_unit": 48_000,
        "vendor": "kmitl_demo.vendor_demo_005",
        "budget_account": "budget.budget_account_5104010208",
        "fund": "account_analytic_kmitl.fund_0200",
        "source": "account_analytic_kmitl.source_2",
        "activity": "account_analytic_kmitl.activity_06",
        "dept": "account_analytic_kmitl.dept_01",
        "department": "kmitl_demo.01",
        "operating_unit": "operating_unit_kmitl.operating_unit_01",
        "proc_type": "purchase_request_kmitl.procurement_type_005",
        "payment_type": "advance",
    },
    {
        "title": "[E2E-DR] จ้างที่ปรึกษา (ค่าผู้เชี่ยวชาญ)",
        "description": "จ้างที่ปรึกษา/ผู้เชี่ยวชาญด้านวิจัย",
        "price_unit": 65_000,
        "vendor": "kmitl_demo.vendor_demo_013",
        "budget_account": "budget.budget_account_5104030202",
        "fund": "account_analytic_kmitl.fund_0300",
        "source": "account_analytic_kmitl.source_2",
        "activity": "account_analytic_kmitl.activity_00",
        "dept": "account_analytic_kmitl.dept_01",
        "department": "kmitl_demo.01",
        "operating_unit": "operating_unit_kmitl.operating_unit_01",
        "proc_type": "purchase_request_kmitl.procurement_type_007",
        "payment_type": "prepaid",
    },
    {
        "title": "[E2E-DR] จ้างเหมาบริการทำความสะอาด",
        "description": "จ้างเหมาบริการดูแลความสะอาดอาคาร",
        "price_unit": 55_000,
        "vendor": "kmitl_demo.vendor_demo_015",
        "budget_account": "budget.budget_account_5104010203",
        "fund": "account_analytic_kmitl.fund_0100",
        "source": "account_analytic_kmitl.source_1",
        "activity": "account_analytic_kmitl.activity_09",
        "dept": "account_analytic_kmitl.dept_01",
        "department": "kmitl_demo.01",
        "operating_unit": "operating_unit_kmitl.operating_unit_01",
        "proc_type": "purchase_request_kmitl.procurement_type_007",
        "payment_type": "direct",
    },
    {
        "title": "[E2E-DR] จ้างซ่อมแซมและบำรุงรักษาครุภัณฑ์",
        "description": "ซ่อมบำรุงครุภัณฑ์สำนักงาน",
        "price_unit": 38_000,
        "vendor": "kmitl_demo.vendor_demo_017",
        "budget_account": "budget.budget_account_5104010204",
        "fund": "account_analytic_kmitl.fund_0500",
        "source": "account_analytic_kmitl.source_2",
        "activity": "account_analytic_kmitl.activity_06",
        "dept": "account_analytic_kmitl.dept_01",
        "department": "kmitl_demo.01",
        "operating_unit": "operating_unit_kmitl.operating_unit_01",
        "proc_type": "purchase_request_kmitl.procurement_type_007",
        "payment_type": "direct",
    },
    {
        "title": "[E2E-DR] จ้างซ่อมแซมและบำรุงรักษาสิ่งก่อสร้าง",
        "description": "ปรับปรุงซ่อมแซมอาคาร",
        "price_unit": 72_000,
        "vendor": "kmitl_demo.vendor_demo_006",
        "budget_account": "budget.budget_account_5104010206",
        "fund": "account_analytic_kmitl.fund_0400",
        "source": "account_analytic_kmitl.source_3",
        "activity": "account_analytic_kmitl.activity_06",
        "dept": "account_analytic_kmitl.dept_01",
        "department": "kmitl_demo.01",
        "operating_unit": "operating_unit_kmitl.operating_unit_01",
        "proc_type": "purchase_request_kmitl.procurement_type_006",
        "payment_type": "direct",
    },
    {
        "title": "[E2E-DR] ค่าใช้จ่ายในการจัดอบรมของหน่วยงาน",
        "description": "จัดอบรมสัมมนาเพื่อพัฒนาบุคลากร",
        "price_unit": 60_000,
        "vendor": "kmitl_demo.vendor_demo_007",
        "budget_account": "budget.budget_account_5104010214",
        "fund": "account_analytic_kmitl.fund_0400",
        "source": "account_analytic_kmitl.source_2",
        "activity": "account_analytic_kmitl.activity_06",
        "dept": "account_analytic_kmitl.dept_01",
        "department": "kmitl_demo.01",
        "operating_unit": "operating_unit_kmitl.operating_unit_01",
        "proc_type": "purchase_request_kmitl.procurement_type_007",
        "payment_type": "direct",
    },
]


def _create_dr_pr_with_line(
    env,
    case,
    admin_user,
    fiscal_year,
    admin_employee,
    supervisor_employee,
    wa_committee_employees,
):
    """Create a PR (with line and committees) for the disbursement-flow demo.

    Differs from `_create_pr_with_line` in that budget_account / dept / department /
    operating_unit are read from the case dict (varied per case), and
    procurement_method is locked to procurement_specific to keep is_egp=False.
    """
    activity = env.ref(case["activity"])
    fund = env.ref(case["fund"])
    source = env.ref(case["source"])
    dept = env.ref(case["dept"])
    department = env.ref(case["department"])
    operating_unit = env.ref(case["operating_unit"])
    budget_account = env.ref(case["budget_account"])
    vendor = env.ref(case["vendor"])
    procurement_type = env.ref(case["proc_type"])
    procurement_method = env.ref("purchase_request_kmitl.procurement_specific")

    # prepaid (สำรองจ่าย) requires an internal-employee partner; use the
    # admin employee's work contact instead of the external vendor.
    payment_type = case["payment_type"]
    partner = (
        admin_employee.work_contact_id
        if payment_type == "prepaid"
        else vendor
    )

    if payment_type == "prepaid" and not partner.partner_type_id.is_internal:
        partner.partner_type_id = env.ref("partner_type_kmitl.partner_type_employee")

    pr = env["purchase.request"].create(
        {
            "title": case["title"],
            "description": case["description"],
            "account_fiscal_year_id": fiscal_year.id,
            "procurement_type_id": procurement_type.id,
            "procurement_method_id": procurement_method.id,
            "payment_type": payment_type,
            "requested_by": admin_user.id,
            "partner_id": partner.id,
            "user_id": admin_user.id,
            "department_id": department.id,
            "operating_unit_id": operating_unit.id,
            "budget_account_id": budget_account.id,
            "activity_analytic_id": activity.id,
            "department_analytic_id": dept.id,
            "fund_analytic_id": fund.id,
            "source_analytic_id": source.id,
        }
    )

    product = budget_account.product_id
    env["purchase.request.line"].create(
        {
            "request_id": pr.id,
            "product_id": product.id,
            "name": product.display_name,
            "product_uom_id": product.uom_id.id,
            "price_unit": case["price_unit"],
            "product_qty": 1.0,
        }
    )

    env["procurement.committee"].create(
        {
            "request_id": pr.id,
            "employee_id": admin_employee.id,
            "committee_type": "work_acceptance",
            "approve_role": "chairman",
            "name": admin_employee.name,
            "phone": admin_employee.work_phone or "",
        }
    )
    for emp in wa_committee_employees:
        env["procurement.committee"].create(
            {
                "request_id": pr.id,
                "employee_id": emp.id,
                "committee_type": "work_acceptance",
                "approve_role": "committee",
                "name": emp.name,
                "phone": emp.work_phone or "",
            }
        )
    env["procurement.committee"].create(
        {
            "request_id": pr.id,
            "employee_id": supervisor_employee.id,
            "committee_type": "work_supervisor",
            "approve_role": "chairman",
            "name": supervisor_employee.name,
            "phone": supervisor_employee.work_phone or "",
        }
    )

    pr.action_ignore_exceptions()
    pr.button_to_verify()

    _logger.info(
        "DR-PR %s created (title=%s, amount=%s, is_egp=%s)",
        pr.name,
        case["title"],
        case["price_unit"],
        pr.is_egp,
    )
    return pr


def _create_wa_and_accept(env, pr, pa, po, admin_employee, wa_committee_employees):
    """Create a Work Acceptance for the given PO/PA pair and accept it.

    Uses paperless tier validation and pre-fills committee status='accept' so
    the WA can be force-accepted via skip_committee_wizard, no UI involved.
    """
    committees = [
        Command.create(
            {
                "employee_id": admin_employee.id,
                "name": admin_employee.name,
                "approve_role": "chairman",
                "status": "accept",
            }
        )
    ]
    for emp in wa_committee_employees:
        committees.append(
            Command.create(
                {
                    "employee_id": emp.id,
                    "name": emp.name,
                    "approve_role": "committee",
                    "status": "accept",
                }
            )
        )

    wa_lines = [
        Command.create(
            {
                "purchase_line_id": line.id,
                "name": line.name,
                "product_uom": line.product_uom.id,
                "product_id": line.product_id.id,
                "price_unit": line.price_unit,
                "product_qty": line._get_product_qty(),
            }
        )
        for line in po.order_line
        if line._get_product_qty() != 0
    ]

    wa = env["work.acceptance"].create(
        {
            "purchase_id": po.id,
            "approval_id": pa.id,
            "partner_id": po.partner_id.id,
            "company_id": po.company_id.id,
            "currency_id": po.currency_id.id,
            "wa_tier_validation": True,
            "wa_line_ids": wa_lines,
            "work_acceptance_committee_ids": committees,
        }
    )
    wa.with_context(skip_committee_wizard=True).button_accept()
    _logger.info(
        "WA %s accepted, completeness=%s, state=%s",
        wa.name,
        wa.completeness,
        wa.state,
    )
    return wa


def _advance_to_disbursement_request(
    env, pr, admin, department, admin_employee, wa_committee_employees
):
    """Drive PR → PA → PO confirm → WA accept → DR created."""
    _run_non_egp_flow(env, pr, admin, department)

    pa = pr.request_approval_ids[:1]
    po = pr.line_ids.purchase_lines.order_id[:1]
    if not pa or not po:
        raise RuntimeError("DR demo flow expected PA and PO for PR %s" % pr.name)

    if po.state in ("draft", "sent"):
        po.button_confirm()
    _logger.info("PO %s confirmed, state=%s", po.name, po.state)

    _create_wa_and_accept(env, pr, pa, po, admin_employee, wa_committee_employees)

    dr = pa._create_disbursement_request()
    _logger.info(
        "DR %s created from PA %s, state=%s, total=%s",
        dr.name,
        pa.name,
        dr.state,
        dr.amount_total,
    )
    return dr


def _create_disbursement_flow_demo(
    env, admin, fiscal_year, admin_employee, supervisor_employee, wa_committee_employees
):
    """Create 10 PR → DR demo records, each with a distinct budget combination."""
    _logger.info("Creating disbursement-flow demo data (10 cases)...")

    # One appropriation per unique (budget_account, activity, fund, source, dept) tuple
    # in DR_CASES. Sized at 1.5× the case price to comfortably cover commitments.
    seen = set()
    for case in DR_CASES:
        key = (
            case["budget_account"],
            case["activity"],
            case["fund"],
            case["source"],
            case["dept"],
        )
        if key in seen:
            continue
        seen.add(key)
        _create_budget_appropriation(
            env,
            env.ref(case["budget_account"]),
            env.ref(case["activity"]),
            env.ref(case["dept"]),
            env.ref(case["fund"]),
            env.ref(case["source"]),
            fiscal_year,
            int(case["price_unit"] * 1.5),
        )

    drs = env["disbursement.request"]
    for i, case in enumerate(DR_CASES, 1):
        _logger.info("=== DR Case %d: %s ===", i, case["title"])
        pr = _create_dr_pr_with_line(
            env,
            case,
            admin_user=admin,
            fiscal_year=fiscal_year,
            admin_employee=admin_employee,
            supervisor_employee=supervisor_employee,
            wa_committee_employees=wa_committee_employees,
        )
        drs |= _advance_to_disbursement_request(
            env,
            pr,
            admin,
            env.ref(case["department"]),
            admin_employee,
            wa_committee_employees,
        )

    _logger.info("Disbursement-flow demo data created successfully! (10 cases)")
    return drs


# === Step B: vendor bills ===
#
# Continue every disbursement request into a posted vendor bill (ตั้งหนี้), which
# leaves it at ``bills_posted``. The payment tail (audit -> authorize -> pay) is
# deliberately not run so the finance payment queue can be demoed by hand.

WHT_DR_INDEX = 7  # one case carries withholding tax


def _create_bill_demo(env, drs):
    """Drive every disbursement request through approval to a posted bill.

    Each DR is advanced inside its own try/except so a failure on one never
    aborts the whole install.
    """
    drs = drs.exists()
    if not drs:
        _logger.warning("finance_kmitl_demo: no disbursement requests to continue.")
        return
    _logger.info("Creating vendor-bill demo from %s disbursement requests...", len(drs))

    try:
        wht_tax = env["account.withholding.tax"].search([], limit=1)
    except KeyError:
        wht_tax = None

    for index, dr in enumerate(drs):
        try:
            # Savepoint per request: swallowing a database-level error without
            # one would leave the transaction aborted for every request after it.
            with env.cr.savepoint():
                _approve_dr(dr)
                _bill_dr(dr, wht_tax if index == WHT_DR_INDEX else None)
        except Exception as error:  # noqa: BLE001 - demo must never abort install
            _logger.warning(
                "finance_kmitl_demo: DR %s stopped before 'bills_posted' (%s)",
                dr.name,
                error,
            )
    _logger.info("Vendor-bill demo created (requests left at 'bills_posted').")


def _dr_commitment(dr):
    """Recover the reserved budget commitment from the originating request.

    The DR created from a purchase request approval (PA) does not carry the
    commitment, so we follow the reference back to the PR which reserved it.
    """
    approval = dr.reference
    if approval and approval._name == "purchase.request.approval":
        return approval.request_id.budget_commitment_id
    return dr.budget_commitment_id


def _approve_dr(dr):
    """Link the reserved commitment and drive the DR draft -> approved."""
    if dr.state != "draft":
        return
    commitment = _dr_commitment(dr)
    if commitment:
        dr.budget_commitment_id = commitment.id
        if commitment.analytic_distribution:
            # The header analytic is required from 'submitted' onwards and is
            # not auto-populated, so copy it from the commitment (4 dimensions).
            dr.analytic_distribution = commitment.analytic_distribution
    dr.ignore_exception = True
    dr.action_submit()
    dr.action_sign()
    dr.action_validate()
    # Two approvers sign off before the budget is committed: the Finance
    # Division Director first, then the Rector-delegated approver.
    dr.action_approve_finance()
    dr.action_approve()


def _bill_dr(dr, wht_tax=None):
    """Create and post the vendor bill, optionally tagging a WHT tax."""
    if wht_tax and dr.line_ids:
        dr.line_ids[:1].wht_tax_id = wht_tax.id
    dr.action_create_bill()
    dr.action_post_bills()


# === Step C: fixed assets and depreciation ===
#
# Create assets directly against the KMITL asset profiles, validate them
# (which computes the depreciation board) and post a few depreciation periods,
# leaving a realistic mix of draft / open / fully depreciated assets.

# (name, profile xmlid, purchase_value, date_start, department xmlid, target)
#   draft        -> created but not validated
#   open         -> validated, depreciation board computed, nothing posted yet
#   depreciated  -> validated, due depreciation periods posted
#   closed       -> old asset, all depreciation posted (fully depreciated)
ASSET_SPECS = [
    (
        "เครื่องคอมพิวเตอร์ All-in-One สำนักงานคณบดี",
        "account_asset_kmitl.asset_profile_014",
        45000.0,
        "2024-10-15",
        "kmitl_demo.01",
        "depreciated",
    ),
    (
        "เครื่องปรับอากาศ ห้องปฏิบัติการ",
        "account_asset_kmitl.asset_profile_001",
        38000.0,
        "2024-11-01",
        "kmitl_demo.01",
        "depreciated",
    ),
    (
        "กล้องจุลทรรศน์ดิจิทัล",
        "account_asset_kmitl.asset_profile_013",
        250000.0,
        "2024-12-20",
        "kmitl_demo.01",
        "depreciated",
    ),
    (
        "เครื่องพิมพ์เลเซอร์มัลติฟังก์ชัน",
        "account_asset_kmitl.asset_profile_001",
        22000.0,
        "2024-10-01",
        "kmitl_demo.89390",
        "depreciated",
    ),
    (
        "รถตู้โดยสาร 12 ที่นั่ง",
        "account_asset_kmitl.asset_profile_002",
        1350000.0,
        "2024-10-20",
        "kmitl_demo.89390",
        "depreciated",
    ),
    (
        "โต๊ะประชุมไม้พร้อมเก้าอี้ 12 ที่นั่ง",
        "account_asset_kmitl.asset_profile_001",
        65000.0,
        "2025-02-10",
        "kmitl_demo.01",
        "open",
    ),
    (
        "เครื่องสำรองไฟ UPS 10kVA",
        "account_asset_kmitl.asset_profile_003",
        90000.0,
        "2025-03-05",
        "kmitl_demo.01",
        "open",
    ),
    (
        "ชุดเครื่องเสียงห้องเรียนอัจฉริยะ",
        "account_asset_kmitl.asset_profile_005",
        75000.0,
        "2025-04-01",
        "kmitl_demo.01",
        "open",
    ),
    (
        "เครื่องวิเคราะห์สเปกตรัม",
        "account_asset_kmitl.asset_profile_013",
        480000.0,
        "2025-05-15",
        "kmitl_demo.01",
        "open",
    ),
    (
        "เครื่องคอมพิวเตอร์โน้ตบุ๊ก (ตัดจำหน่าย)",
        "account_asset_kmitl.asset_profile_014",
        36000.0,
        "2020-01-10",
        "kmitl_demo.01",
        "closed",
    ),
    (
        "ครุภัณฑ์สำนักงานรอตรวจรับ",
        "account_asset_kmitl.asset_profile_001",
        18000.0,
        "2026-01-05",
        "kmitl_demo.01",
        "draft",
    ),
    (
        "เครื่องมือวิทยาศาสตร์รอขึ้นทะเบียน",
        "account_asset_kmitl.asset_profile_013",
        120000.0,
        "2026-02-01",
        "kmitl_demo.01",
        "draft",
    ),
]


def _create_asset_demo(env):
    """Create fixed assets across a mix of states with posted depreciation."""
    _logger.info("Creating fixed-asset demo data (%s assets)...", len(ASSET_SPECS))
    company = env.ref("base.main_company")
    gpsc = env["procurement.gpsc"].search([], limit=1)
    today = fields.Date.context_today(env["account.asset"])

    for name, profile_ref, value, date_start, dept_ref, target in ASSET_SPECS:
        try:
            # Savepoint per asset: swallowing a database-level error without one
            # would leave the transaction aborted for every asset after it.
            with env.cr.savepoint():
                profile = env.ref(profile_ref, raise_if_not_found=False)
                department = env.ref(dept_ref, raise_if_not_found=False)
                if not profile:
                    continue
                start = fields.Date.to_date(date_start)
                fiscal_year = company.find_daterange_fy(start)
                asset = env["account.asset"].create(
                    {
                        "name": name,
                        "profile_id": profile.id,
                        "purchase_value": value,
                        "date_start": date_start,
                        "company_id": company.id,
                        "department_id": department.id if department else False,
                        "account_fiscal_year_id": (
                            fiscal_year.id if fiscal_year else False
                        ),
                        "gpsc_id": gpsc.id if gpsc else False,
                    }
                )
                # Asset numbering needs department short name + GPSC;
                # best-effort, in its own savepoint for the same reason.
                try:
                    with env.cr.savepoint():
                        asset.create_asset_number()
                except Exception as error:  # noqa: BLE001
                    _logger.info("Asset numbering skipped for '%s': %s", name, error)

                if target == "draft":
                    continue

                asset.validate()  # -> open + depreciation board computed
                if target in ("depreciated", "closed"):
                    _post_depreciation(asset, today, all_lines=(target == "closed"))
        except Exception as error:  # noqa: BLE001 - demo must never abort install
            _logger.warning("finance_kmitl_demo: asset '%s' skipped (%s)", name, error)
    _logger.info("Fixed-asset demo data created.")


def _post_depreciation(asset, today, all_lines=False):
    """Post depreciation journal entries for an asset's due lines."""
    lines = asset.depreciation_line_ids.filtered(
        lambda l: l.type == "depreciate" and not l.move_check and not l.init_entry
    ).sorted("line_date")
    if not all_lines:
        lines = lines.filtered(lambda l: l.line_date and l.line_date <= today)
    if lines:
        lines.create_move()
