# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectProject(models.Model):
    _inherit = "project.project"

    code = fields.Char(string="รหัสโครงการ", tracking=True, copy=False)
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="ปีงบประมาณ",
        tracking=True,
        readonly=False,
        copy=False,
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("cancel", "Cancelled"),
            ("confirm", "Confirmed"),
            ("validate", "Validated"),
            ("done", "Done"),
        ],
        string="Status",
        default="draft",
        index=True,
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
    )

    total_budget = fields.Monetary(
        string="จำนวนงบประมาณ",
        tracking=True,
        required=True,
        currency_field="currency_id",
    )

    introduction = fields.Html(
        string="หลักการและเหตุผล", sanitize_attributes=False, tracking=True
    )

    national_strategy_id = fields.Many2one(
        "project.strategic.plan",
        string="ยุทธศาสตร์ชาติ",
        domain="[('level', '=', 1)]",
        tracking=True,
    )

    master_plan_id = fields.Many2one(
        "project.strategic.plan",
        string="แผนแม่บทภายใต้ยุทธศาสตร์ชาติ",
        domain="[('level', '=', 2)]",
        tracking=True,
    )

    nesdc_plan_id = fields.Many2one(
        "project.strategic.plan",
        string="แผนพัฒนาเศรษฐกิจและสังคมแห่งชาติ ฉบับที่ 13",
        domain=lambda self: [("id", "child_of", self.env.ref("project_kmitl.P13").id)],
        tracking=True,
    )

    kmitl_plan_id = fields.Many2one(
        "project.strategic.plan",
        string="แผนกลยุทธสถาบัน",
        domain="[('level', '=', 3)]",
        tracking=True,
    )

    impact_ids = fields.Many2many(
        comodel_name="project.impact",
        string="Impact",
        copy=True,
        tracking=True,
    )

    global_index_ids = fields.Many2many(
        comodel_name="project.global.index",
        string="Global Index",
        copy=True,
        tracking=True,
    )

    fight_ids = fields.Many2many(
        comodel_name="project.fight",
        string="ความสอดคล้องกับค่านิยม : FIGHT",
        copy=True,
        tracking=True,
    )

    methodology_ids = fields.Many2many(
        comodel_name="project.methodology",
        string="วิธีดำเนินการ",
        copy=True,
        tracking=True,
    )

    methodology_detail = fields.Text("วิธีดำเนินการ (รายละเอียด)", copy=True, tracking=True)

    location = fields.Text(string="สถานที่/พื้นที่ดำเนินโครงการ", copy=True, tracking=True)

    objective_ids = fields.One2many(
        "project.objective", "project_id", string="วัตถุประสงค์ของโครงการ"
    )

    target_ids = fields.One2many(
        "project.target",
        "project_id",
        string="กลุ่มเป้าหมาย/ผู้ดำเนินโครงการ",
        domain=[("line_type", "=", "target")],
    )

    participant_ids = fields.One2many(
        "project.target",
        "project_id",
        string="กลุ่มเป้าหมาย/ผู้ดำเนินโครงการ",
        domain=[("line_type", "=", "participant")],
    )

    organizer_ids = fields.One2many(
        "project.target",
        "project_id",
        string="กลุ่มเป้าหมาย/ผู้ดำเนินโครงการ",
        domain=[("line_type", "=", "organizer")],
    )

    output_ids = fields.One2many(
        "project.output",
        "project_id",
        string="ผลผลิต",
        domain=[("line_type", "=", "output")],
    )

    outcome_ids = fields.One2many(
        "project.output",
        "project_id",
        string="ผลลัพธ์",
        domain=[("line_type", "=", "outcome")],
    )

    plan_ids = fields.One2many(
        "project.plan", "project_id", string="แผนการดำเนินงานและแผนการใช้จ่ายงบประมาณ"
    )

    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        domain=[("res_model", "=", "project.project")],
        string="Attachments",
    )

    expected_outcome_ids = fields.One2many(
        "project.expected.outcome", "project_id", string="ผลที่คาดว่าจะได้รับ"
    )

    evaluation_ids = fields.Many2many(
        comodel_name="project.evaluation",
        string="วิธีการ/เครื่องมือติดตามและประเมินผล",
        copy=True,
        tracking=True,
    )

    evaluation_detail = fields.Text(
        "วิธีการ/เครื่องมือติดตามและประเมินผล (รายละเอียด)", copy=True, tracking=True
    )
