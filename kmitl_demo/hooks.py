import logging

from odoo import SUPERUSER_ID, api
from odoo.fields import Command

_logger = logging.getLogger(__name__)


def post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Install the Thai language pack
    th = (
        env["res.lang"].with_context(active_test=False).search([("code", "=", "th_TH")])
    )
    ll = env["base.language.install"].create(
        {"lang_ids": [Command.clear(), Command.link(th.id)]}
    )
    ll.lang_install()

    # Set the default language for the system to Thai
    default_lang = env["ir.default"].browse([1])
    default_lang.json_value = '"th_TH"'

    # Set the default language for all users to Thai
    users = env["res.users"].search([])
    users.lang = "th_TH"

    # Create end-to-end purchase request → purchase order demo data
    _create_e2e_purchase_demo(env)


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    default_lang = env["ir.default"].browse([1])
    default_lang.json_value = '"en_US"'

    users = env["res.users"].search([])
    users.lang = "en_US"

    rl = env["res.lang"].search([("code", "=", "th_TH")])
    rl.active = False


# === End-to-end purchase demo data ===

# 10 test cases covering all payment types, procurement types, methods, EGP/non-EGP
E2E_CASES = [
    # Group A: fund_0200 + source_2 + activity_06
    {
        "title": "[E2E] ซื้อวัสดุสำนักงาน (จ่ายตรง)",
        "description": "จัดซื้อวัสดุสำนักงาน เฉพาะเจาะจง จ่ายตรง",
        "price_unit": 45_000,
        "payment_type": "direct",
        "proc_type": "purchase_request_kmitl.procurement_type_004",
        "proc_method": "purchase_request_kmitl.procurement_specific",
        "vendor": "kmitl_demo.vendor_demo_004",
        "fund": "account_analytic_kmitl.fund_0200",
        "source": "account_analytic_kmitl.source_2",
        "activity": "account_analytic_kmitl.activity_06",
    },
    {
        "title": "[E2E] เช่าเครื่องถ่ายเอกสาร (ยืมเงิน)",
        "description": "เช่าเครื่องถ่ายเอกสาร เฉพาะเจาะจง ยืมเงิน",
        "price_unit": 72_000,
        "payment_type": "advance",
        "proc_type": "purchase_request_kmitl.procurement_type_005",
        "proc_method": "purchase_request_kmitl.procurement_specific",
        "vendor": "kmitl_demo.vendor_demo_005",
        "fund": "account_analytic_kmitl.fund_0200",
        "source": "account_analytic_kmitl.source_2",
        "activity": "account_analytic_kmitl.activity_06",
    },
    {
        "title": "[E2E] จ้างปรับปรุงห้องปฏิบัติการ (EGP, E-bidding)",
        "description": "จ้างก่อสร้างปรับปรุงห้องปฏิบัติการ E-bidding EGP",
        "price_unit": 2_500_000,
        "payment_type": "advance",
        "proc_type": "purchase_request_kmitl.procurement_type_006",
        "proc_method": "purchase_request_kmitl.procurement_bidding",
        "vendor": "kmitl_demo.vendor_demo_006",
        "fund": "account_analytic_kmitl.fund_0200",
        "source": "account_analytic_kmitl.source_2",
        "activity": "account_analytic_kmitl.activity_06",
        "egp_project_id": "12345678",
    },
    # Group B: fund_0100 + source_1 + activity_09
    {
        "title": "[E2E] ซื้อครุภัณฑ์คอมพิวเตอร์ (งบแผ่นดิน, คัดเลือก)",
        "description": "จัดซื้อครุภัณฑ์คอมพิวเตอร์ งบแผ่นดิน คัดเลือก EGP",
        "price_unit": 800_000,
        "payment_type": "direct",
        "proc_type": "purchase_request_kmitl.procurement_type_004",
        "proc_method": "purchase_request_kmitl.procurement_select",
        "vendor": "kmitl_demo.vendor_demo_002",
        "fund": "account_analytic_kmitl.fund_0100",
        "source": "account_analytic_kmitl.source_1",
        "activity": "account_analytic_kmitl.activity_09",
        "egp_project_id": "12345678",
    },
    {
        "title": "[E2E] จ้างเหมาบริการทำความสะอาด (งบแผ่นดิน)",
        "description": "จ้างทำของ/จ้างเหมาบริการ งบแผ่นดิน เฉพาะเจาะจง ใกล้ EGP",
        "price_unit": 95_000,
        "payment_type": "direct",
        "proc_type": "purchase_request_kmitl.procurement_type_007",
        "proc_method": "purchase_request_kmitl.procurement_specific",
        "vendor": "kmitl_demo.vendor_demo_015",
        "fund": "account_analytic_kmitl.fund_0100",
        "source": "account_analytic_kmitl.source_1",
        "activity": "account_analytic_kmitl.activity_09",
    },
    {
        "title": "[E2E] ซื้อเครื่องมือวิทยาศาสตร์ (งบแผ่นดิน, ประกาศทั่วไป)",
        "description": "จัดซื้อเครื่องมือวิทยาศาสตร์ งบแผ่นดิน ประกาศเชิญชวนทั่วไป EGP",
        "price_unit": 3_200_000,
        "payment_type": "advance",
        "proc_type": "purchase_request_kmitl.procurement_type_004",
        "proc_method": "purchase_request_kmitl.procurement_general",
        "vendor": "kmitl_demo.vendor_demo_008",
        "fund": "account_analytic_kmitl.fund_0100",
        "source": "account_analytic_kmitl.source_1",
        "activity": "account_analytic_kmitl.activity_09",
        "egp_project_id": "12345678",
    },
    # Group C: fund_0300 + source_2 + activity_00
    {
        "title": "[E2E] จ้างที่ปรึกษาวิจัย (กองทุนวิจัย, จ่ายล่วงหน้า)",
        "description": "จ้างทำของ/จ้างเหมาบริการที่ปรึกษาวิจัย กองทุนวิจัย จ่ายล่วงหน้า",
        "price_unit": 85_000,
        "payment_type": "prepaid",
        "proc_type": "purchase_request_kmitl.procurement_type_007",
        "proc_method": "purchase_request_kmitl.procurement_specific",
        "vendor": "kmitl_demo.vendor_demo_013",
        "fund": "account_analytic_kmitl.fund_0300",
        "source": "account_analytic_kmitl.source_2",
        "activity": "account_analytic_kmitl.activity_00",
    },
    {
        "title": "[E2E] ซื้ออุปกรณ์ห้องปฏิบัติการ (กองทุนวิจัย, EGP)",
        "description": "จัดซื้ออุปกรณ์ห้องปฏิบัติการ กองทุนวิจัย EGP จ่ายล่วงหน้า",
        "price_unit": 450_000,
        "payment_type": "prepaid",
        "proc_type": "purchase_request_kmitl.procurement_type_004",
        "proc_method": "purchase_request_kmitl.procurement_specific",
        "vendor": "kmitl_demo.vendor_demo_009",
        "fund": "account_analytic_kmitl.fund_0300",
        "source": "account_analytic_kmitl.source_2",
        "activity": "account_analytic_kmitl.activity_00",
        "egp_project_id": "12345678",
    },
    # Group D: fund_0400 + source_2 + activity_06
    {
        "title": "[E2E] เช่าเครื่องมือวัด (กองทุนบริการวิชาการ)",
        "description": "เช่าเครื่องมือวัด กองทุนบริการวิชาการ ยืมเงิน",
        "price_unit": 65_000,
        "payment_type": "advance",
        "proc_type": "purchase_request_kmitl.procurement_type_005",
        "proc_method": "purchase_request_kmitl.procurement_specific",
        "vendor": "kmitl_demo.vendor_demo_017",
        "fund": "account_analytic_kmitl.fund_0400",
        "source": "account_analytic_kmitl.source_2",
        "activity": "account_analytic_kmitl.activity_06",
    },
    {
        "title": "[E2E] จ้างก่อสร้างห้องเรียนอัจฉริยะ (EGP, E-bidding)",
        "description": "จ้างก่อสร้างห้องเรียนอัจฉริยะ กองทุนบริการวิชาการ E-bidding EGP",
        "price_unit": 5_000_000,
        "payment_type": "direct",
        "proc_type": "purchase_request_kmitl.procurement_type_006",
        "proc_method": "purchase_request_kmitl.procurement_bidding",
        "vendor": "kmitl_demo.vendor_demo_007",
        "fund": "account_analytic_kmitl.fund_0400",
        "source": "account_analytic_kmitl.source_2",
        "activity": "account_analytic_kmitl.activity_06",
        "egp_project_id": "12345678",
    },
]

# Budget appropriation groups: (activity, fund, source, amount)
BUDGET_GROUPS = [
    (
        "account_analytic_kmitl.activity_06",
        "account_analytic_kmitl.fund_0200",
        "account_analytic_kmitl.source_2",
        3_000_000,
    ),
    (
        "account_analytic_kmitl.activity_09",
        "account_analytic_kmitl.fund_0100",
        "account_analytic_kmitl.source_1",
        5_000_000,
    ),
    (
        "account_analytic_kmitl.activity_00",
        "account_analytic_kmitl.fund_0300",
        "account_analytic_kmitl.source_2",
        1_000_000,
    ),
    (
        "account_analytic_kmitl.activity_06",
        "account_analytic_kmitl.fund_0400",
        "account_analytic_kmitl.source_2",
        6_000_000,
    ),
]


def _create_budget_appropriation(
    env, budget_account, activity, dept, fund, source, fiscal_year, amount
):
    """Create and post a budget appropriation move."""
    move = env["budget.move"].create(
        {
            "move_type": "appropriation",
            "budget_type": "expense",
            "account_fiscal_year_id": fiscal_year.id,
            "department_analytic_id": dept.id,
            "source_analytic_id": source.id,
            "line_ids": [
                Command.create(
                    {
                        "account_id": budget_account.id,
                        "debit": amount,
                        "balance": amount,
                        "fund_analytic_id": fund.id,
                        "analytic_distribution": {
                            str(activity.id): 100,
                            str(fund.id): 100,
                        },
                    }
                )
            ],
        }
    )
    move.action_post()
    _logger.info("Budget appropriation %s posted (amount=%s)", move.name, amount)
    return move


def _process_sarabun_approve(env, origin_record, admin_user, department):
    """Drive sarabun document from creation through approval."""
    result = origin_record.action_submit_to_sarabun()
    doc = env["sarabun.document"].browse(result.get("res_id"))

    # Add routing line: admin as approver
    env["sarabun.routing.line"].create(
        {
            "document_id": doc.id,
            "sequence": 100,
            "routing_type": "approve",
            "recipient_type": "user",
            "user_id": admin_user.id,
        }
    )

    # Set required fields
    doc.recipient = "ผู้บริหาร"

    # Send document
    doc.action_send()

    # Approve as admin (switch user since post_init runs as SUPERUSER_ID)
    doc_as_admin = doc.with_user(admin_user)
    recipient = doc_as_admin.recipient_ids.filtered(lambda r: r.state == "new")
    role = env.ref("agx_sarabun.role_system_admin")
    recipient.with_user(admin_user).action_do_approve(signed_as_role_id=role.id)

    _logger.info(
        "Sarabun %s completed for %s,%s",
        doc.name,
        origin_record._name,
        origin_record.id,
    )
    return doc


def _create_pr_with_line(
    env,
    case,
    admin_user,
    fiscal_year,
    budget_account,
    dept,
    department,
    operating_unit,
    admin_employee,
    supervisor_employee,
    wa_committee_employees=None,
):
    """Create a purchase request with line and committees."""
    activity = env.ref(case["activity"])
    fund = env.ref(case["fund"])
    source = env.ref(case["source"])
    vendor = env.ref(case["vendor"])
    procurement_type = env.ref(case["proc_type"])
    procurement_method = env.ref(case["proc_method"])

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
            "egp_project_id": case.get("egp_project_id"),
        }
    )

    # Create PR line
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

    # Work acceptance committee: admin as sole chairman
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

    # Work acceptance committee members
    for emp in wa_committee_employees or []:
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

    # Work supervisor: separate employee (constraint forbids same as work_acceptance)
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

    # Ignore exceptions and verify
    pr.action_ignore_exceptions()
    pr.button_to_verify()

    _logger.info(
        "PR %s created (title=%s, amount=%s)",
        pr.name,
        case["title"],
        case["price_unit"],
    )
    return pr


def _run_non_egp_flow(env, pr, admin_user, department):
    """Run non-EGP flow: PR → Sarabun → PA → Sarabun → PO."""
    pr.action_reserve_budget()
    _logger.info("PR %s budget reserved, state=%s", pr.name, pr.state)

    _process_sarabun_approve(env, pr, admin_user, department)
    _logger.info("PR %s sarabun approved, state=%s", pr.name, pr.state)

    pa = pr.request_approval_ids[0]
    _logger.info("PA %s auto-created, state=%s", pa.name, pa.state)

    _process_sarabun_approve(env, pa, admin_user, department)
    _logger.info("PA %s sarabun approved, state=%s", pa.name, pa.state)

    pr.approval_make_purchase_order()
    _logger.info("PR %s PO created, purchase_count=%s", pr.name, pr.purchase_count)


def _run_egp_flow(env, pr, admin_user, department):
    """Run EGP flow: PR → Sarabun → egp_in_progress → PO (no PA)."""
    pr.action_reserve_budget()
    _logger.info("PR %s budget reserved, state=%s", pr.name, pr.state)

    _process_sarabun_approve(env, pr, admin_user, department)
    _logger.info(
        "PR %s sarabun approved, state=%s, egp_status=%s",
        pr.name,
        pr.state,
        pr.egp_status,
    )

    pr.action_egp_in_progress()
    _logger.info("PR %s egp_status=%s", pr.name, pr.egp_status)

    wizard = (
        env["purchase.request.line.make.purchase.order"]
        .with_context(
            active_model="purchase.request",
            active_ids=pr.ids,
            active_id=pr.id,
        )
        .create({"supplier_id": pr.partner_id.id})
    )
    wizard.make_purchase_order()
    _logger.info("PR %s EGP PO created, purchase_count=%s", pr.name, pr.purchase_count)


def _create_e2e_purchase_demo(env):
    """Create 10 end-to-end PR → PO demo records"""
    _logger.info("Creating end-to-end purchase demo data (10 cases)...")

    # Resolve shared references
    admin = env.ref("base.user_admin")
    fiscal_year = env.ref("kmitl_demo.account_fiscal_year_y2569")
    budget_account = env.ref("budget.budget_account_5101020008")
    dept = env.ref("account_analytic_kmitl.dept_01")
    department = env.ref("kmitl_demo.01")
    operating_unit = env.ref("operating_unit_kmitl.operating_unit_01")

    # Admin employee for work_acceptance committee
    admin_employee = env["hr.employee"].search([("user_id", "=", admin.id)], limit=1)
    # Separate employee for work_supervisor (constraint forbids same as work_acceptance)
    supervisor_employee = env.ref("kmitl_demo.employee_demo_008")

    # Work acceptance committee members (คณะกรรมการตรวจรับพัสดุ)
    wa_committee_employees = (
        env.ref("kmitl_demo.employee_demo_012")  # ชนิดา
        + env.ref("kmitl_demo.employee_demo_011")  # พิชัย
        + env.ref("kmitl_demo.employee_demo_020")  # ปิยะนุช
        + env.ref("kmitl_demo.employee_demo_018")  # สุดารัตน์
    )

    # Create budget appropriations for each financial dimension group
    for activity_ref, fund_ref, source_ref, amount in BUDGET_GROUPS:
        _create_budget_appropriation(
            env,
            budget_account,
            env.ref(activity_ref),
            dept,
            env.ref(fund_ref),
            env.ref(source_ref),
            fiscal_year,
            amount,
        )

    # Process each case
    for i, case in enumerate(E2E_CASES, 1):
        _logger.info("=== Case %d: %s ===", i, case["title"])
        pr = _create_pr_with_line(
            env,
            case,
            admin_user=admin,
            fiscal_year=fiscal_year,
            budget_account=budget_account,
            dept=dept,
            department=department,
            operating_unit=operating_unit,
            admin_employee=admin_employee,
            supervisor_employee=supervisor_employee,
            wa_committee_employees=wa_committee_employees,
        )

        if pr.is_egp:
            _run_egp_flow(env, pr, admin, department)
        else:
            _run_non_egp_flow(env, pr, admin, department)

    _logger.info("End-to-end purchase demo data created successfully! (10 cases)")
