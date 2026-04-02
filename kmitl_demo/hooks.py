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


def _create_budget_appropriation(
    env, budget_account, activity, dept, fund, source, fiscal_year, amount
):
    """Create and post a budget appropriation move."""
    analytic_distribution = {
        str(activity.id): 100,
        str(fund.id): 100,
    }
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
                        "analytic_distribution": analytic_distribution,
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

    # Approve as admin (must switch to admin user since post_init runs as SUPERUSER_ID)
    admin_env = env(user=admin_user)
    doc_as_admin = doc.with_env(admin_env)
    recipient = doc_as_admin.recipient_ids.filtered(lambda r: r.state == "new")
    role = admin_env.ref("agx_sarabun.role_system_admin")
    recipient.action_do_approve(signed_as_role_id=role.id)

    _logger.info(
        "Sarabun %s completed for %s,%s",
        doc.name,
        origin_record._name,
        origin_record.id,
    )
    return doc


def _create_pr_with_line(
    env,
    title,
    description,
    price_unit,
    payment_type,
    admin_user,
    fiscal_year,
    budget_account,
    activity,
    dept,
    fund,
    source,
    vendor,
    department,
    procurement_type,
    procurement_method,
    employees,
):
    """Create a purchase request with line and committees."""
    pr = env["purchase.request"].create(
        {
            "title": title,
            "description": description,
            "account_fiscal_year_id": fiscal_year.id,
            "procurement_type_id": procurement_type.id,
            "procurement_method_id": procurement_method.id,
            "payment_type": payment_type,
            "requested_by": admin_user.id,
            "partner_id": vendor.id,
            "user_id": admin_user.id,
            "department_id": department.id,
            "budget_account_id": budget_account.id,
            "activity_analytic_id": activity.id,
            "department_analytic_id": dept.id,
            "fund_analytic_id": fund.id,
            "source_analytic_id": source.id,
        }
    )

    # Create PR line (like _onchange_budget_account_id does)
    product = budget_account.product_id
    env["purchase.request.line"].create(
        {
            "request_id": pr.id,
            "product_id": product.id,
            "name": product.display_name,
            "product_uom_id": product.uom_id.id,
            "price_unit": price_unit,
            "product_qty": 1.0,
        }
    )

    # Add work acceptance committees
    for i, (emp, role) in enumerate(
        [
            (employees[0], "chairman"),
            (employees[1], "committee"),
            (employees[2], "committee"),
        ]
    ):
        env["procurement.committee"].create(
            {
                "request_id": pr.id,
                "employee_id": emp.id,
                "committee_type": "work_acceptance",
                "approve_role": role,
                "name": emp.name,
                "phone": emp.work_phone or "",
            }
        )

    # Ignore exceptions and verify
    pr.action_ignore_exceptions()
    pr.button_to_verify()

    _logger.info("PR %s created (title=%s, amount=%s)", pr.name, title, price_unit)
    return pr


def _run_non_egp_flow(env, pr, admin_user, department):
    """Run non-EGP flow: PR → Sarabun → PA → Sarabun → PO."""
    # Reserve budget → moves to to_approve
    pr.action_reserve_budget()
    _logger.info("PR %s budget reserved, state=%s", pr.name, pr.state)

    # Sarabun approve → moves to approved
    _process_sarabun_approve(env, pr, admin_user, department)
    _logger.info("PR %s sarabun approved, state=%s", pr.name, pr.state)

    # Create PA
    pr.button_create_approval()
    pa = pr.request_approval_ids[0]
    _logger.info("PA %s created, state=%s", pa.name, pa.state)

    # Validate PA
    pa.button_validate()
    _logger.info("PA %s validated, state=%s", pa.name, pa.state)

    # Sarabun approve PA → moves to approved
    _process_sarabun_approve(env, pa, admin_user, department)
    _logger.info("PA %s sarabun approved, state=%s", pa.name, pa.state)

    # Create PO from approval
    pr.approval_make_purchase_order()
    _logger.info(
        "PR %s PO created, purchase_count=%s", pr.name, pr.purchase_count
    )


def _run_egp_flow(env, pr, admin_user, department):
    """Run EGP flow: PR → Sarabun → egp_in_progress → PO (no PA)."""
    # Reserve budget → moves to to_approve
    pr.action_reserve_budget()
    _logger.info("PR %s budget reserved, state=%s", pr.name, pr.state)

    # Sarabun approve → moves to approved, egp_status set to "waiting"
    _process_sarabun_approve(env, pr, admin_user, department)
    _logger.info(
        "PR %s sarabun approved, state=%s, egp_status=%s",
        pr.name,
        pr.state,
        pr.egp_status,
    )

    # Move EGP to in_progress
    pr.action_egp_in_progress()
    _logger.info("PR %s egp_status=%s", pr.name, pr.egp_status)

    # Create PO via wizard (same pattern as _create_purchase_order_from_approval)
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
    _logger.info(
        "PR %s EGP PO created, purchase_count=%s", pr.name, pr.purchase_count
    )


def _create_e2e_purchase_demo(env):
    """Create 3 end-to-end PR → PO demo records."""
    _logger.info("Creating end-to-end purchase demo data...")

    # Resolve references
    admin = env.ref("base.user_admin")
    fiscal_year = env.ref("kmitl_demo.account_fiscal_year_y2569")
    budget_account = env.ref("budget.budget_account_5101020008")
    activity = env.ref("account_analytic_kmitl.activity_06")
    dept = env.ref("account_analytic_kmitl.dept_01")
    fund = env.ref("account_analytic_kmitl.fund_0200")
    source = env.ref("account_analytic_kmitl.source_2")
    vendor = env.ref("kmitl_demo.vendor_demo_014")
    department = env.ref("kmitl_demo.01")
    procurement_type = env.ref("purchase_request_kmitl.procurement_type_006")
    procurement_method = env.ref("purchase_request_kmitl.procurement_general")
    employees = [
        env.ref("kmitl_demo.employee_demo_005"),
        env.ref("kmitl_demo.employee_demo_007"),
        env.ref("kmitl_demo.employee_demo_008"),
    ]

    # Shared PR creation kwargs
    shared = dict(
        admin_user=admin,
        fiscal_year=fiscal_year,
        budget_account=budget_account,
        activity=activity,
        dept=dept,
        fund=fund,
        source=source,
        vendor=vendor,
        department=department,
        procurement_type=procurement_type,
        procurement_method=procurement_method,
        employees=employees,
    )

    # Step A: Create budget appropriation (20M to cover all cases)
    _create_budget_appropriation(
        env, budget_account, activity, dept, fund, source, fiscal_year, 20_000_000
    )

    # Step B: Case 1 — Non-EGP Direct Payment (50K)
    _logger.info("=== Case 1: Non-EGP Direct 50K ===")
    pr1 = _create_pr_with_line(
        env,
        title="[E2E] จัดซื้อวัสดุสำนักงาน",
        description="จัดซื้อวัสดุสำนักงานสำหรับทดสอบระบบ (direct payment)",
        price_unit=50000,
        payment_type="direct",
        **shared,
    )
    _run_non_egp_flow(env, pr1, admin, department)

    # Step C: Case 2 — Non-EGP Loan Payment (80K)
    _logger.info("=== Case 2: Non-EGP Loan 80K ===")
    pr2 = _create_pr_with_line(
        env,
        title="[E2E] จัดจ้างซ่อมแซมอุปกรณ์",
        description="จัดจ้างซ่อมแซมอุปกรณ์สำหรับทดสอบระบบ (loan payment)",
        price_unit=80000,
        payment_type="loan",
        **shared,
    )
    _run_non_egp_flow(env, pr2, admin, department)

    # Step D: Case 3 — EGP (5M)
    _logger.info("=== Case 3: EGP 5M ===")
    pr3 = _create_pr_with_line(
        env,
        title="[E2E] จัดซื้อครุภัณฑ์คอมพิวเตอร์",
        description="จัดซื้อครุภัณฑ์คอมพิวเตอร์สำหรับทดสอบระบบ (EGP >100K)",
        price_unit=5_000_000,
        payment_type="loan",
        **shared,
    )
    _run_egp_flow(env, pr3, admin, department)

    _logger.info("End-to-end purchase demo data created successfully!")
