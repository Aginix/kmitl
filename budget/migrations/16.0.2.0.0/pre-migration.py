import logging

_logger = logging.getLogger(__name__)

# The budget-transfer feature moved to its own `budget_transfer` module
# (ADR-0013). On this upgrade `budget` no longer declares the transfer records,
# so its own `_process_end` would delete them (and unlinking the `ir.model`
# rows would DROP the tables). Hand ownership of everything the new module
# re-declares over to `budget_transfer` *first* — it is auto-installed in the
# same run and re-owns them cleanly. `budget.transfer.line` is deliberately NOT
# re-owned: its model is folded into `budget.move.line`, so let budget's
# process_end reap the leftover model + table.

# Data xmlids the `budget_transfer` module re-declares by name.
_XMLIDS = (
    # views
    "view_budget_transfer_form",
    "view_budget_transfer_tree",
    "view_budget_transfer_search",
    "view_budget_transfer_kanban",
    # actions
    "action_budget_transfer",
    "action_my_budget_transfers",
    "action_budget_transfers_pending",
    # menus
    "budget_transfer_management",
    "budget_transfer_menu",
    "action_my_budget_transfers_menu",
    "action_budget_transfers_pending_menu",
    "action_budget_transfer_menu",
    # sequence
    "seq_budget_transfer",
    # email templates
    "email_template_budget_transfer_submitted",
    "email_template_budget_transfer_approved",
    "email_template_budget_transfer_rejected",
    "email_template_budget_transfer_posted",
    # security (the folded line's rows are dropped, not moved)
    "access_budget_transfer_user",
    "access_budget_transfer_viewer",
    "access_budget_transfer_reject_wizard_user",
)

# Models whose ir.model / ir.model.fields metadata xmlids move with the code.
_KEPT_MODELS = ("budget.transfer", "budget.transfer.reject.wizard")


def migrate(cr, version):
    # 1) Named data records.
    cr.execute(
        """
        UPDATE ir_model_data
           SET module = 'budget_transfer'
         WHERE module = 'budget'
           AND name IN %s
        """,
        (_XMLIDS,),
    )
    moved_data = cr.rowcount

    # 2) ir.model metadata for the kept models.
    cr.execute(
        """
        UPDATE ir_model_data d
           SET module = 'budget_transfer'
          FROM ir_model m
         WHERE d.module = 'budget'
           AND d.model = 'ir.model'
           AND d.res_id = m.id
           AND m.model IN %s
        """,
        (_KEPT_MODELS,),
    )

    # 3) ir.model.fields metadata for the kept models. Stale fields that the
    #    transfer no longer owns itself (date, company_id, … — now delegated to
    #    budget.move) ride along and are reaped at budget_transfer's own
    #    process_end, dropping their leftover columns.
    cr.execute(
        """
        UPDATE ir_model_data d
           SET module = 'budget_transfer'
          FROM ir_model_fields f
         WHERE d.module = 'budget'
           AND d.model = 'ir.model.fields'
           AND d.res_id = f.id
           AND f.model IN %s
        """,
        (_KEPT_MODELS,),
    )

    # 4) Drop the now-orphan reverse column on budget.move: the transfer used to
    #    stamp budget.move.transfer_id; it now owns move_id, and the reverse is
    #    the computed transfer_ids one2many (budget_transfer.budget.move).
    cr.execute("ALTER TABLE budget_move DROP COLUMN IF EXISTS transfer_id")

    _logger.info(
        "budget_transfer split: re-owned %s named record(s) + model/field "
        "metadata for %s; dropped budget_move.transfer_id",
        moved_data,
        ", ".join(_KEPT_MODELS),
    )
