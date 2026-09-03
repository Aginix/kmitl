# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# แหล่งเงิน 7 รหัส split into the two paths money actually travels: 1/3/5 are
# government-budget codes (เส้นแผ่นดิน), 2/4/6/7 are the institute's own revenue
# (เส้นรายได้). Named by the external ids account_analytic_kmitl already seeds
# (data/account.analytic.account.xml), never by searching on code, so a chart
# that renamed or renumbered them still resolves the right accounts.
GOV_SOURCES = ("source_1", "source_3", "source_5")
REV_SOURCES = ("source_2", "source_4", "source_6", "source_7")

# One row per (paying account × source group), reverse-engineered from
# accounting's own ledger (วิธีการบันทึกบัญชี-ค่าตอบแทน.xlsx). ``hops`` lists the
# intermediate accounts in order, source account first, paying account itself
# excluded — empty means the paying account is spent directly out of, which is
# accounting's real practice for the two savings accounts (rows *_direct).
#
# Government-budget money for the three cheque-only-until-now paying accounts
# (SCB 171-2, KTB 42-8, BAY 033-8) is routed through the same GOV pair every
# other GOV route uses (1112110012 -> 1112120025) before continuing on to
# wherever the matching REV route already lands — the two paths only diverge
# at the source end, not at the paying-account end.
CASH_ROUTES = [
    # REV: the four paying accounts already wired for เงินโอน.
    {
        "xmlid": "route_1112120003_rev",
        "account": "1112120003",
        "sources": REV_SOURCES,
        "hops": ("1112210004", "1112220015"),
    },
    {
        "xmlid": "route_1112120002_rev",
        "account": "1112120002",
        "sources": REV_SOURCES,
        "hops": ("1112210004", "1112220015"),
    },
    {
        "xmlid": "route_1112120006_rev",
        "account": "1112120006",
        "sources": REV_SOURCES,
        "hops": ("1112210004", "1112220015"),
    },
    {
        "xmlid": "route_1112120016_rev",
        "account": "1112120016",
        "sources": REV_SOURCES,
        "hops": ("1112210004", "1112220015"),
    },
    # REV: the three paying accounts this module adds (account_kmitl.hooks).
    {
        "xmlid": "route_1112220005_rev",
        "account": "1112220005",
        "sources": REV_SOURCES,
        "hops": ("1112210004",),
    },
    {
        "xmlid": "route_1112220016_rev",
        "account": "1112220016",
        "sources": REV_SOURCES,
        "hops": ("1112210001",),
    },
    {
        "xmlid": "route_1112220012_rev",
        "account": "1112220012",
        "sources": REV_SOURCES,
        "hops": ("1112210009",),
    },
    # GOV: the same four paying accounts, government-budget path.
    {
        "xmlid": "route_1112120003_gov",
        "account": "1112120003",
        "sources": GOV_SOURCES,
        "hops": ("1112110012", "1112120025"),
    },
    {
        "xmlid": "route_1112120002_gov",
        "account": "1112120002",
        "sources": GOV_SOURCES,
        "hops": ("1112110012", "1112120025"),
    },
    {
        "xmlid": "route_1112120006_gov",
        "account": "1112120006",
        "sources": GOV_SOURCES,
        "hops": ("1112110012", "1112120025"),
    },
    {
        "xmlid": "route_1112120016_gov",
        "account": "1112120016",
        "sources": GOV_SOURCES,
        "hops": ("1112110012", "1112120025"),
    },
    # GOV: the three new paying accounts, chained through the GOV pair and
    # then on through the matching REV route's own hop.
    {
        "xmlid": "route_1112220005_gov",
        "account": "1112220005",
        "sources": GOV_SOURCES,
        "hops": ("1112110012", "1112120025", "1112210004"),
    },
    {
        "xmlid": "route_1112220016_gov",
        "account": "1112220016",
        "sources": GOV_SOURCES,
        "hops": ("1112110012", "1112120025", "1112210001"),
    },
    {
        "xmlid": "route_1112220012_gov",
        "account": "1112220012",
        "sources": GOV_SOURCES,
        "hops": ("1112110012", "1112120025", "1112210009"),
    },
    # Direct: the two savings/fallback accounts money is sometimes drawn on
    # itself. Zero hops is accounting's real practice, not a gap — it is what
    # keeps the "no route found" exception from firing on these.
    {
        "xmlid": "route_1112210004_rev_direct",
        "account": "1112210004",
        "sources": REV_SOURCES,
        "hops": (),
    },
    {
        "xmlid": "route_1112110012_gov_direct",
        "account": "1112110012",
        "sources": GOV_SOURCES,
        "hops": (),
    },
    # The same two current accounts, this time as the paying account for a
    # cheque rather than as an intermediate hop for a transfer elsewhere.
    {
        "xmlid": "route_1112220015_rev",
        "account": "1112220015",
        "sources": REV_SOURCES,
        "hops": ("1112210004",),
    },
    {
        "xmlid": "route_1112120025_gov",
        "account": "1112120025",
        "sources": GOV_SOURCES,
        "hops": ("1112110012",),
    },
]


def _seed_cash_routes(env):
    """Create the inter-account cash routes and publish their external ids.

    Idempotent, and deliberately never overwrites: a route already present —
    under its external id, or under the same (paying account, source) found by
    hand — is adopted as-is and only gains its external id if it lacked one.
    This is accounting's own configuration once it exists.

    A paying account, source of funds, or intermediate account the chart does
    not have costs one skipped route and one warning, never the install: the
    chart is not guaranteed to carry every account this table names, and
    guessing a substitute would send the file's "which account" reasoning
    somewhere nobody chose.
    """
    company = env.ref("base.main_company")
    Account = env["account.account"]
    Route = env["kmitl.cash.route"]
    made, adopted, skipped = [], [], []

    def get_account(code):
        return Account.search(
            [("code", "=", code), ("company_id", "=", company.id)], limit=1
        )

    for entry in CASH_ROUTES:
        xml_id = "disbursement_cash_movement_kmitl.%s" % entry["xmlid"]
        route = env.ref(xml_id, raise_if_not_found=False)
        if route:
            adopted.append(route.display_name)
            continue

        paying_account = get_account(entry["account"])
        sources = env["account.analytic.account"].browse()
        missing = []
        for source_xmlid in entry["sources"]:
            source = env.ref(
                "account_analytic_kmitl.%s" % source_xmlid, raise_if_not_found=False
            )
            if source:
                sources |= source
            else:
                missing.append(source_xmlid)
        if not paying_account or missing:
            skipped.append(
                "%s (%s)"
                % (
                    entry["xmlid"],
                    "no paying account %s" % entry["account"]
                    if not paying_account
                    else "missing source(s) %s" % ", ".join(missing),
                )
            )
            continue

        hop_accounts = []
        missing_hops = []
        for code in entry["hops"]:
            account = get_account(code)
            if account:
                hop_accounts.append(account)
            else:
                missing_hops.append(code)
        if missing_hops:
            skipped.append(
                "%s (missing intermediate account(s) %s)"
                % (entry["xmlid"], ", ".join(missing_hops))
            )
            continue

        existing = Route.search(
            [
                ("paying_gl_account_id", "=", paying_account.id),
                ("company_id", "=", company.id),
                ("source_analytic_ids", "in", sources.ids),
            ],
            limit=1,
        )
        if existing:
            env["ir.model.data"]._update_xmlids(
                [{"xml_id": xml_id, "record": existing, "noupdate": True}]
            )
            adopted.append(existing.display_name)
            continue

        route = Route.create(
            {
                "paying_gl_account_id": paying_account.id,
                "source_analytic_ids": [(6, 0, sources.ids)],
                "company_id": company.id,
                "hop_ids": [
                    (0, 0, {"sequence": (index + 1) * 10, "account_id": account.id})
                    for index, account in enumerate(hop_accounts)
                ],
            }
        )
        env["ir.model.data"]._update_xmlids(
            [{"xml_id": xml_id, "record": route, "noupdate": True}]
        )
        made.append(route.display_name)

    if made:
        _logger.info(
            "disbursement_cash_movement_kmitl: created cash route(s): %s.",
            ", ".join(made),
        )
    if adopted:
        _logger.info(
            "disbursement_cash_movement_kmitl: cash route(s) already present, "
            "left as they are: %s.",
            ", ".join(adopted),
        )
    if skipped:
        _logger.warning(
            "disbursement_cash_movement_kmitl: could not create cash route(s): "
            "%s — set them up in Accounting ▸ Configuration ▸ Cash Routes.",
            "; ".join(skipped),
        )
    return True


def _repair_payment_subject_person_budget(env):
    """Move a subject seeded before this feature existed off the REV savings
    account it was wrongly falling back to for GOV money.

    ``payment_subject_person_budget`` (จ่ายบุคคล…เงินงบประมาณ) shipped with
    ``1112210004`` — the REV savings account — as both its default and its
    fallback in ``allowed_paying_account_ids``; it should have been
    ``1112110012``, the GOV one, or a payee falling back ends up on an account
    this module's routes only ever cover for REV sources. Fixed at the source
    in ``finance_kmitl/hooks.py``, but that module's own ``post_init_hook``
    never re-runs on a database where it is already installed, and its seed
    never overwrites a subject that already exists (it is master data finance
    may have since adjusted) — so the corrected table alone never reaches an
    installed database. Repaired here instead, at the moment this feature is
    installed, since that is exactly when the wrong fallback starts costing a
    payee their cash-movement legs.

    Idempotent and narrow: only a subject still pointing at the exact old line
    is touched, so one finance has already repointed by hand is left alone.
    """
    subject = env.ref(
        "finance_kmitl.payment_subject_person_budget", raise_if_not_found=False
    )
    old_line = env.ref(
        "account_kmitl.paying_account_1112210004_transfer", raise_if_not_found=False
    )
    new_line = env.ref(
        "account_kmitl.paying_account_1112110012_transfer", raise_if_not_found=False
    )
    if not subject or not old_line or not new_line:
        return
    if subject.default_paying_account_id == old_line:
        subject.default_paying_account_id = new_line.id
        _logger.info(
            "disbursement_cash_movement_kmitl: repaired %s's default paying "
            "account from %s to %s.",
            subject.display_name,
            old_line.display_name,
            new_line.display_name,
        )
    if old_line in subject.allowed_paying_account_ids:
        subject.allowed_paying_account_ids = [(3, old_line.id), (4, new_line.id)]
        _logger.info(
            "disbursement_cash_movement_kmitl: repaired %s's allowed paying "
            "accounts to use %s instead of %s.",
            subject.display_name,
            new_line.display_name,
            old_line.display_name,
        )


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _repair_payment_subject_person_budget(env)
    _seed_cash_routes(env)
