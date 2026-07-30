"""Post-init demo data for the KMITL post-budget finance flow.

Four demo stories run in order from ``post_init``:

* the disbursement flow (``PR -> PA -> PO -> Work Acceptance -> DR``), moved here
  from ``kmitl_demo``;
* vendor bills, payments and a KTB bank payment export built from those DRs;
* fixed assets with posted depreciation;
* standalone outbound vendor payments (draft/submitted) to fill the payment
  list and treasury reports with data.

The disbursement flow reuses two helpers from ``kmitl_demo`` (the purchase
end-to-end flow uses them too) instead of duplicating them.
"""
import logging
from datetime import timedelta

from odoo import SUPERUSER_ID, api, fields
from odoo.exceptions import UserError
from odoo.fields import Command

from odoo.addons.kmitl_demo.hooks import (
    _create_budget_appropriation,
    _run_non_egp_flow,
)

_logger = logging.getLogger(__name__)


def post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    drs = _create_disbursement_flow_demo(
        env,
        admin=env.ref("base.user_admin"),
        fiscal_year=env.ref("kmitl_demo.account_fiscal_year_y2568"),
        admin_employee=_admin_employee(env),
        supervisor_employee=env.ref("kmitl_demo.employee_demo_008"),
        wa_committee_employees=_wa_committee_employees(env),
    )
    _create_bill_payment_demo(env, drs)
    _create_asset_demo(env)
    _create_standalone_payment_demo(env)


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

    pr = env["purchase.request"].create(
        {
            "title": case["title"],
            "description": case["description"],
            "account_fiscal_year_id": fiscal_year.id,
            "procurement_type_id": procurement_type.id,
            "procurement_method_id": procurement_method.id,
            "payment_type": case["payment_type"],
            "requested_by": admin_user.id,
            "partner_id": vendor.id,
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


# === Step B: bills, payments and bank export ===
#
# Continue the disbursement requests into vendor bills (ตั้งหนี้), payments
# (ล้างหนี้/จ่าย) and a KTB bank payment export. Each DR is advanced to a
# different stage so the accounting tail shows records in every state.

# Target stage per DR (by position), giving a realistic mix across the whole
# post-bill payment-execution workflow:
#   approve    -> approved, ready to bill
#   bill       -> vendor bill posted (bills_posted)
#   audit      -> audited by the payment auditor (payment_audited)
#   authorize  -> authorized to pay (payment_authorized)
#   payment    -> draft payment created, awaiting bank confirmation
#   paid       -> bank result confirmed success (paid), awaiting accounting
#   pay        -> accounting posted the payment (cleared / ล้างหนี้)
DR_STAGE_TARGETS = [
    "approve",
    "bill",
    "audit",
    "authorize",
    "payment", "payment",
    "paid",
    "pay", "pay", "pay",
]
WHT_DR_INDEX = 7  # one "pay" (cleared) case carries withholding tax


def _create_bill_payment_demo(env, drs):
    """Drive the disbursement requests through billing and payment.

    Each DR is advanced inside its own try/except so a failure on one never
    aborts the whole install.
    """
    drs = drs.exists()
    if not drs:
        _logger.warning(
            "finance_kmitl_demo: no disbursement requests to continue."
        )
        return
    _logger.info(
        "Creating bill/payment demo from %s disbursement requests...", len(drs)
    )

    try:
        wht_tax = env["account.withholding.tax"].search([], limit=1)
    except KeyError:
        wht_tax = None

    for index, dr in enumerate(drs):
        target = (
            DR_STAGE_TARGETS[index]
            if index < len(DR_STAGE_TARGETS)
            else "approve"
        )
        try:
            _approve_dr(dr)
            if target == "approve":
                continue
            _bill_dr(dr, wht_tax if index == WHT_DR_INDEX else None)
            if target == "bill":
                continue
            _classify_dr(env, dr)
            dr.action_audit()
            if target == "audit":
                continue
            dr.action_authorize()
            if target == "authorize":
                continue
            dr.action_create_payment()
            if target == "payment":
                continue
            _finalize_payment(env, dr, do_clear=(target == "pay"))
        except Exception as error:  # noqa: BLE001 - demo must never abort install
            _logger.warning(
                "finance_kmitl_demo: DR %s stopped before '%s' (%s)",
                dr.name,
                target,
                error,
            )
    _logger.info("Bill/payment demo created.")


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


def _demo_paying_account(env, company, bank):
    """Flag a KTB bank account in the chart as a paying account (หัวจ่าย)."""
    account = env["account.account"].search(
        [
            ("company_id", "=", company.id),
            ("is_paying_account", "=", True),
            ("paying_bank_id", "=", bank.id if bank else False),
        ],
        limit=1,
    )
    if account:
        return account
    account = env["account.account"].search(
        [("company_id", "=", company.id), ("account_type", "=", "asset_cash")],
        limit=1,
    )
    if not account:
        return account
    account.write({
        "is_paying_account": True,
        "paying_bank_id": bank.id if bank else False,
        "paying_acc_number": "0281038783",
    })
    return account


def _classify_dr(env, dr):
    """Auditor's payment classification demo: subject, paying account, banks.

    Uses the "จ่ายตรงคู่ค้า" subject bound to a KTB paying account, and gives
    every payee a bank account so the transfer lines pass the audit validation.
    """
    subject = env.ref(
        "finance_kmitl.payment_subject_vendor_direct",
        raise_if_not_found=False,
    )
    if not subject:
        return
    ktb_bank = env["res.bank"].search([("bic", "=", "KRTHTHBK")], limit=1)
    paying_account = _demo_paying_account(env, dr.company_id, ktb_bank)
    if paying_account and not subject.allowed_paying_account_ids:
        subject.write({
            "allowed_paying_account_ids": [(6, 0, paying_account.ids)],
            "default_paying_account_id": paying_account.id,
        })
    dr.payment_subject_id = subject
    for partner in dr.line_ids.partner_id:
        if not partner.bank_ids:
            env["res.partner.bank"].create({
                "partner_id": partner.id,
                "acc_number": "999%07d" % partner.id,
                "bank_id": ktb_bank.id if ktb_bank else False,
            })
    for line in dr.line_ids.filtered(lambda l: not l.partner_bank_id):
        line.partner_bank_id = line.partner_id.bank_ids[:1]
    # Fills method + paying account per line, matching the payee's bank.
    dr._apply_subject_defaults(dr.line_ids)


def _finalize_payment(env, dr, do_clear):
    """Send the payment to the bank, confirm the result (-> paid) and, for a
    "pay" target, let accounting post the payment move (-> cleared).

    Best-effort: a missing bank configuration leaves the request at 'paid'
    (bank confirmed) rather than aborting the module installation.
    """
    payments = dr.payment_ids.filtered(lambda p: p.state == "draft")
    if not payments:
        return
    payments.action_submit()
    exported = _export_payments(env, payments)
    # Finance confirms the bank result (success) so the request can reach 'paid'.
    lines = env["bank.payment.export.line"].search(
        [("payment_id", "in", payments.ids)]
    )
    if lines:
        lines._apply_epayment_result("success")
    else:
        payments.write({"bank_result_status": "success"})
    dr.action_confirm_paid()
    if do_clear and exported:
        # Accounting posts the payment move (guard passes: paid + success),
        # which reconciles against the bill and clears the request.
        to_post = payments.filtered(
            lambda p: p.state == "submitted" and p.export_status != "draft"
        )
        to_post.action_post()


def _export_payments(env, payments):
    """Best-effort KTB bank export of the given submitted payments.

    The full KTB export depends on company bank configuration (bank journal
    BIC, export format) that may be absent on a given database. Returns True
    when the export was confirmed, False otherwise.
    """
    try:
        for payment in payments:
            ktb_bank = payment.partner_id.bank_ids.filtered(
                lambda bank: bank.bank_id.bic == "KRTHTHBK"
            )[:1]
            if ktb_bank:
                payment.partner_bank_id = ktb_bank.id

        export = env["bank.payment.export"].create(
            {"bank": "KRTHTHBK", "company_id": payments[:1].company_id.id}
        )
        export.action_get_all_payments()
        if not export.export_line_ids:
            raise UserError("No submitted payments available to export.")
        for line in export.export_line_ids:
            if not line.payment_partner_bank_id and line.payment_id.partner_bank_id:
                line.payment_partner_bank_id = line.payment_id.partner_bank_id.id
        export.write(
            {
                "ktb_bank_type": "direct",
                "ktb_service_type_direct": "14",
                "effective_date": fields.Date.context_today(export),
            }
        )
        export.action_confirm()
        _logger.info("Bank export %s confirmed.", export.name)
        return True
    except Exception as error:  # noqa: BLE001 - best-effort, keep install green
        _logger.warning(
            "finance_kmitl_demo: bank export skipped (best-effort): %s",
            error,
        )
        return False


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
    ("เครื่องคอมพิวเตอร์ All-in-One สำนักงานคณบดี",
     "account_asset_kmitl.asset_profile_014", 45000.0, "2024-10-15",
     "kmitl_demo.01", "depreciated"),
    ("เครื่องปรับอากาศ ห้องปฏิบัติการ",
     "account_asset_kmitl.asset_profile_001", 38000.0, "2024-11-01",
     "kmitl_demo.01", "depreciated"),
    ("กล้องจุลทรรศน์ดิจิทัล",
     "account_asset_kmitl.asset_profile_013", 250000.0, "2024-12-20",
     "kmitl_demo.01", "depreciated"),
    ("เครื่องพิมพ์เลเซอร์มัลติฟังก์ชัน",
     "account_asset_kmitl.asset_profile_001", 22000.0, "2024-10-01",
     "kmitl_demo.89390", "depreciated"),
    ("รถตู้โดยสาร 12 ที่นั่ง",
     "account_asset_kmitl.asset_profile_002", 1350000.0, "2024-10-20",
     "kmitl_demo.89390", "depreciated"),
    ("โต๊ะประชุมไม้พร้อมเก้าอี้ 12 ที่นั่ง",
     "account_asset_kmitl.asset_profile_001", 65000.0, "2025-02-10",
     "kmitl_demo.01", "open"),
    ("เครื่องสำรองไฟ UPS 10kVA",
     "account_asset_kmitl.asset_profile_003", 90000.0, "2025-03-05",
     "kmitl_demo.01", "open"),
    ("ชุดเครื่องเสียงห้องเรียนอัจฉริยะ",
     "account_asset_kmitl.asset_profile_005", 75000.0, "2025-04-01",
     "kmitl_demo.01", "open"),
    ("เครื่องวิเคราะห์สเปกตรัม",
     "account_asset_kmitl.asset_profile_013", 480000.0, "2025-05-15",
     "kmitl_demo.01", "open"),
    ("เครื่องคอมพิวเตอร์โน้ตบุ๊ก (ตัดจำหน่าย)",
     "account_asset_kmitl.asset_profile_014", 36000.0, "2020-01-10",
     "kmitl_demo.01", "closed"),
    ("ครุภัณฑ์สำนักงานรอตรวจรับ",
     "account_asset_kmitl.asset_profile_001", 18000.0, "2026-01-05",
     "kmitl_demo.01", "draft"),
    ("เครื่องมือวิทยาศาสตร์รอขึ้นทะเบียน",
     "account_asset_kmitl.asset_profile_013", 120000.0, "2026-02-01",
     "kmitl_demo.01", "draft"),
]


def _create_asset_demo(env):
    """Create fixed assets across a mix of states with posted depreciation."""
    _logger.info("Creating fixed-asset demo data (%s assets)...", len(ASSET_SPECS))
    company = env.ref("base.main_company")
    gpsc = env["procurement.gpsc"].search([], limit=1)
    today = fields.Date.context_today(env["account.asset"])

    for name, profile_ref, value, date_start, dept_ref, target in ASSET_SPECS:
        try:
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
                    "account_fiscal_year_id": fiscal_year.id if fiscal_year else False,
                    "gpsc_id": gpsc.id if gpsc else False,
                }
            )
            # Asset numbering needs department short name + GPSC; best-effort.
            try:
                asset.create_asset_number()
            except Exception as error:  # noqa: BLE001
                _logger.info("Asset numbering skipped for '%s': %s", name, error)

            if target == "draft":
                continue

            asset.validate()  # -> open + depreciation board computed
            if target in ("depreciated", "closed"):
                _post_depreciation(asset, today, all_lines=(target == "closed"))
        except Exception as error:  # noqa: BLE001 - demo must never abort install
            _logger.warning(
                "finance_kmitl_demo: asset '%s' skipped (%s)", name, error
            )
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


# === Step D: standalone vendor payments ===
#
# 50 outbound (supplier) payments created directly, cycling through the demo
# vendors, dimensions, amounts and dates. They are NOT linked to vendor bills so
# the install stays fast; half are left in ``draft`` and half ``submitted`` so
# the payment list and treasury reports show data in both states.

STANDALONE_PAYMENT_COUNT = 50
# (activity, fund, source, dept) — dimension xmlids reused from DR_CASES.
STANDALONE_PAYMENT_DIMENSIONS = [
    ("activity_09007", "fund_0600", "source_1", "dept_89390"),
    ("activity_06", "fund_0200", "source_2", "dept_01"),
    ("activity_09", "fund_0100", "source_1", "dept_01"),
    ("activity_00", "fund_0300", "source_2", "dept_01"),
    ("activity_06", "fund_0500", "source_2", "dept_01"),
    ("activity_06", "fund_0400", "source_3", "dept_01"),
]
STANDALONE_PAYMENT_MEMOS = [
    "ค่าวัสดุสำนักงาน",
    "ค่าวัสดุคอมพิวเตอร์",
    "ค่าวัสดุวิทยาศาสตร์",
    "ค่าจ้างเหมาบริการทำความสะอาด",
    "ค่าซ่อมแซมและบำรุงรักษาครุภัณฑ์",
    "ค่าเช่าอุปกรณ์สำนักงาน",
    "ค่าที่ปรึกษา/ผู้เชี่ยวชาญ",
    "ค่าจัดอบรมสัมมนา",
    "ค่าโปรแกรมคอมพิวเตอร์",
    "ค่าจ้างเหมาบริการทั่วไป",
]


def _create_standalone_payment_demo(env):
    """Create standalone outbound vendor payments across draft/submitted.

    Payments are created directly (not from a bill) so the install stays fast,
    and each one is built inside its own try/except so a failure never aborts
    the install.

    Must run after the Story B bank export: that export grabs every submitted
    payment company-wide, so creating these submitted payments earlier would
    pull them into it unintentionally.
    """
    company = env.ref("base.main_company")
    fiscal_year = env.ref("kmitl_demo.account_fiscal_year_y2568")
    payment_type = env.ref(
        "finance_kmitl.payment_type_normal_outbound",
        raise_if_not_found=False,
    )
    journal = env["account.journal"].search(
        [("type", "=", "bank"), ("company_id", "=", company.id)],
        limit=1,
    )
    if not payment_type or not journal:
        _logger.warning(
            "finance_kmitl_demo: standalone payments skipped "
            "(missing outbound payment type or bank journal)."
        )
        return

    _logger.info(
        "Creating standalone payment demo (%s records)...",
        STANDALONE_PAYMENT_COUNT,
    )
    currency = journal.currency_id or company.currency_id
    created = 0
    for index in range(STANDALONE_PAYMENT_COUNT):
        try:
            vendor = env.ref(
                "kmitl_demo.vendor_demo_%03d" % (index % 20 + 1),
                raise_if_not_found=False,
            )
            if not vendor:
                continue
            dimensions = STANDALONE_PAYMENT_DIMENSIONS[
                index % len(STANDALONE_PAYMENT_DIMENSIONS)
            ]
            accounts = [
                env.ref("account_analytic_kmitl.%s" % code, raise_if_not_found=False)
                for code in dimensions
            ]
            analytic = {account.id: 100 for account in accounts if account}
            memo = STANDALONE_PAYMENT_MEMOS[index % len(STANDALONE_PAYMENT_MEMOS)]
            payment = env["account.payment"].create(
                {
                    "partner_id": vendor.id,
                    "partner_type": "supplier",
                    "payment_type": "outbound",
                    "kmitl_payment_type_id": payment_type.id,
                    "journal_id": journal.id,
                    "currency_id": currency.id,
                    "amount": 5000 + (index % 20) * 1850 + index * 25,
                    "date": fiscal_year.date_from + timedelta(days=index * 7),
                    "ref": "[DEMO-PAY] %s #%02d" % (memo, index + 1),
                    "analytic_distribution": analytic,
                }
            )
            # Leave half draft, half submitted so both states show in the list.
            if index % 2 == 0:
                payment.action_submit()
            created += 1
        except Exception as error:  # noqa: BLE001 - demo must never abort install
            _logger.warning(
                "finance_kmitl_demo: standalone payment #%s skipped (%s)",
                index + 1,
                error,
            )
    _logger.info("Standalone payment demo created (%s records).", created)
