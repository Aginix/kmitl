import logging

from odoo import tools
from odoo import Command, api, fields, models

_logger = logging.getLogger(__name__)


class MisReportF3p003(models.AbstractModel):
    _name = _description = "mis.report.kmitl.f3_p_003_overall"

    revenues = [
        {"name": "rev", "description": "รายรับ", "line_type": "str"},
        {
            "name": "rev_kmitl",
            "description": "เงินรายได้สถาบัน",
            "children": [
                {
                    "name": "rev_r49000",
                    "description": "ค่าธรรมเนียมการศึกษา และค่าธรรมเนียมอื่น ๆ",
                    "account": ["43100","43200","4121010099","4124000004","4121010025","4121010026","4121010050","4121010054","4121010059","4121010060","4121010061","4121010062","4121010063","4121010094","4121010200","4121010092","4121010010","4121010011","4121010051","4121010052","4121010053","4121010013","4121010014","4121010017","4121010022","4121010023","4121010024","4121020004","4121020007","4121020008","4121020003","4121020099","4121020015","4121020002","4121020001","4121020097","4121020098"],
                },
                {
                    "name": "rev_43300",
                    "description": "รายได้จากงานบริการ",
                    "account": ["4121030016","4121030003","4121030001","4121030017","4121030096","4121030097","4121030099","4121030098","4121030006","4121030007","4121030008","4121030009","4121030010","4121030012","4121030011","4121030014","4121030013","4121030005","4121030015","4121030004"],
                },
                {
                    "name": "rev_43400",
                    "description": "รายได้จากเงินผลประโยชน์",
                    "account": ["4121040022","4121040001","4121040002","4121040003","4121040004","4121040005","4121040006","4121040048","4121040049","4121040007","4121040008","4121040009","4121040010","4121040036","4121040037","4121040038","4121040050","4121040039","4121040041","4121040034","4121040028","4121040029","4121040031","4121040032","4121040033","4121040018","4121040019","4121040099","4121040051","4121040096","4121040097","4121040098","4121040021","4121040023","4121040024","4121040025","4121040026","4121040027","4121040035","4121040042","4121040043","4121040044","4121040045","4121040046","4121040047","4121040012","4121040013","4121040015","4121040016","4121040017"],
                },
                {
                    "name": "rev_interest",
                    "description": "รายได้ดอกเบี้ย",
                    "account": ["4123000002", "4123000001"],
                },
                {
                    "name": "rev_43500",
                    "description": "รายได้จากการรับบริจาค หรือ เงินอุดหนุน",
                    "account": ["4122000025","4122000024","4122000023","4122000021","4122000018","4122000001","4122000002","4122000003","4122000004","4122000005","4122000006","4122000008","4122000009","4122000011","4122000012","4122000014","4122000016","4122000015","4122000017","43600","2210000005","2210000001","2210000002","2210000003","2210000004","2230000004","2210000006","2210000007","2210000008","2210000009","2210000010","2210000011","2210000012","2210000013","2210000027","2230000003"],
                },
                {
                    "name": "rev_43700",
                    "description": "รายได้อื่น",
                    "account": ["4121050002","4121050011","4121050010","4121050009","4121050008","4121050007","4121050004","4121050001","4121050005","4121050003","4121050006"],
                },
            ],
        },
    ]

    # level 1, 2
    expenses = [
        {"name": "exp", "description": "รายจ่าย", "line_type": "str"},
        {
            "name": "exp_51000",
            "description": "1. งบบุคลากร",
            "children": [
                {
                    "name": "exp_5101010007",
                    "description": "เงินประจําตําแหน่งผู้เชี่ยวชาญ",
                    "account": ["5101010007"],
                },
                {
                    "name": "exp_5101010006",
                    "description": "เงินประจําตําแหน่งทางวิชาการ",
                    "account": ["5101010006"],
                },
                {
                    "name": "exp_5101010004",
                    "description": "เงินประจําตําแหน่งผู้บริหาร",
                    "account": ["5101010004"],
                },
                {
                    "name": "exp_5101010020",
                    "description": "เงินประจําตําแหน่งวิชาชีพเฉพาะ 120",
                    "account": ["5101010020"],
                },
                {
                    "name": "exp_5101010017",
                    "description": "ค่าจ้างลูกจ้างสัญญาจ้างพนักงาน",
                    "account": ["5101010017"],
                },
                {
                    "name": "exp_5101010012",
                    "description": "เงินตอบแทนพิเศษของลูกจ้างประจําผู้ได้รับค่าจ้างถึงขั้นสูงของตําแหน่ง-173-340",
                    "account": ["5101010012"],
                },
                {
                    "name": "exp_5101010015",
                    "description": "เงินรางวัลสําหรับผู้บริหาร",
                    "account": ["5101010015"],
                },
                {
                    "name": "exp_5101010009",
                    "description": "ค่าครองชีพลูกจ้างชั่วคราวเงินรายได้",
                    "account": ["5101010009"],
                },
                {
                    "name": "exp_5101010001",
                    "description": "เงินเดือน",
                    "account": ["5101010001"],
                },
                {
                    "name": "exp_5101010022",
                    "description": "ค่าครองชีพชั่วคราวสําหรับข้าราชการ 180",
                    "account": ["5101010022"],
                },
                {
                    "name": "exp_5101010040",
                    "description": "ค่าจ้างพนักงานสถาบันประเภทพื้นฐาน",
                    "account": ["5101010040"],
                },
                {
                    "name": "exp_5101010099",
                    "description": "เงินเดือนและค่าจ้างอื่น",
                    "account": ["5101010099"],
                },
                {
                    "name": "exp_5101010023",
                    "description": "เงินสมนาคุณนายกสภา(ส่วนที่ต้องสมทบเงินงบประมาณแผ่นดิน)",
                    "account": ["5101010023"],
                },
                {
                    "name": "exp_5101010039",
                    "description": "ค่าตอบแทนการใช้ภาษาต่างประเทศ",
                    "account": ["5101010039"],
                },
                {
                    "name": "exp_5101010003",
                    "description": "ค่าจ้างชั่วคราว",
                    "account": ["5101010003"],
                },
                {
                    "name": "exp_5101010005",
                    "description": "เงินประจําตําแหน่งวิชาชีพเฉพาะ/ชํานาญการ",
                    "account": ["5101010005"],
                },
                {
                    "name": "exp_5101010013",
                    "description": "เงินโบนัส",
                    "account": ["5101010013"],
                },
                {
                    "name": "exp_5101010021",
                    "description": "ค่าครองชีพชั่วคราวสําหรับลูกจ้างประจํา 181",
                    "account": ["5101010021"],
                },
                {
                    "name": "exp_5101010016",
                    "description": "เงินรางวัลสําหรับหน่วยงาน",
                    "account": ["5101010016"],
                },
                {
                    "name": "exp_5101010025",
                    "description": "ค่าครองชีพชั่วคราวพนักงานเงินรายได้",
                    "account": ["5101010025"],
                },
                {
                    "name": "exp_5101010011",
                    "description": "เงินตอบแทนพิเศษของข้าราชการผู้ได้รับเงินเดือนถึงขั้นสูงของอันดับ-172-330",
                    "account": ["5101010011"],
                },
                {
                    "name": "exp_5101010038",
                    "description": "ค่าจ้างพนักงานสถาบันประเภทพิเศษ",
                    "account": ["5101010038"],
                },
                {
                    "name": "exp_5101010002",
                    "description": "ค่าจ้างประจํา",
                    "account": ["5101010002"],
                },
                {
                    "name": "exp_51200",
                    "description": "ค่าใช้จ่ายบุคลากรอื่น",
                    "account": [
                        "5101020000",
                        "5101020052",
                        "5101020001",
                        "5101020004",
                        "5101020005",
                        "5101030100",
                        "5101020003",
                        "5101020053",
                        "5101020055",
                        "5101020002",
                        "5101020045",
                        "5101020006",
                        "5101020051",
                        "5101030101",
                        "5101030200",
                        "5101030103",
                        "5101030102",
                        "5101040100",
                        "5101030208",
                        "5101030207",
                        "5101030206",
                        "5101030205",
                        "5101030245",
                        "5101030203",
                        "5101030202",
                        "5101030201",
                        "5101030209",
                        "5101040101",
                        "5101040104",
                        "5101040200",
                        "5101040120",
                        "5101040105",
                        "5101040201",
                        "5101040202",
                        "5101040203",
                        "5101050100",
                        "5101050101",
                    ],
                },
            ],
        },
        {
            "name": "exp_52000",
            "description": "2. งบดำเนินงาน",
            "children": [
                {
                    "name": "exp_52301",
                    "description": "ค่าตอบแทน",
                    "account": [
                        "5230000000",
                        "5101020025",
                        "5101020017",
                        "5101020018",
                        "5101020011",
                        "5101020125",
                        "5101020126",
                        "5101020127",
                        "5101020010",
                        "5101020012",
                        "5101020013",
                        "5101020021",
                        "5101020022",
                        "5101020044",
                        "5101020104",
                        "5101020114",
                        "5101020115",
                        "5104030201",
                        "5101020117",
                        "5101010010",
                        "5101020032",
                        "5101020020",
                        "5101020023",
                        "5101020046",
                        "5101020033",
                        "5101020037",
                        "5101020106",
                        "5101020118",
                        "5101020119",
                        "5101020120",
                        "5101020121",
                        "5101020122",
                        "5101020123",
                        "5101020124",
                        "5101020019",
                        "5101020009",
                        "5101020008",
                        "5101020024",
                        "5101020026",
                        "5101020027",
                        "5101020028",
                        "5101020029",
                        "5101020030",
                        "5101020031",
                        "5101020014",
                        "5101020015",
                        "5101020016",
                    ],
                },
                {
                    "name": "exp_52400",
                    "description": "ค่าใช้สอย",
                    "account": [
                        "5104010200",
                        "5104010209",
                        "5104010208",
                        "5104010201",
                        "5104010206",
                        "5104010204",
                        "5104010202",
                        "5104010212",
                        "5104010205",
                        "5104010298",
                        "5104010218",
                        "5104010216",
                        "5104010285",
                        "5104010291",
                        "5104010299",
                        "5104030202",
                        "5104010219",
                        "5104010214",
                        "5104010215",
                        "5104030203",
                        "5102010000",
                        "5104010203",
                        "5104010211",
                        "5104010207",
                        "5104010210",
                        "5104010220",
                        "5102010001",
                        "5102020000",
                        "5102010099",
                        "5102010002",
                        "5102010004",
                        "5102010003",
                        "5103010000",
                        "5102020001",
                        "5102020002",
                        "5102020003",
                        "5102020004",
                        "5102020099",
                        "5103010001",
                        "5103010002",
                        "5103010003",
                        "5103010099",
                        "5103020000",
                        "5103020099",
                        "5103020003",
                        "5104030100",
                        "5103020001",
                        "5103020002",
                        "5104030101",
                        "5104030102",
                    ],
                },
                {
                    "name": "exp_52500",
                    "description": "ค่าวัสดุ",
                    "account": [
                        "5104010000",
                        "5104010109",
                        "5104010112",
                        "5104010199",
                        "5104010111",
                        "5104010107",
                        "5104010108",
                        "5104010116",
                        "5104010115",
                        "5104010105",
                        "5104010103",
                        "5104010101",
                        "5104010106",
                        "5104010104",
                        "5104010114",
                        "5104010113",
                        "5104010102",
                        "5104010110",
                        "5104010198",
                    ],
                },
                {
                    "name": "exp_52600",
                    "description": "ค่าสาธารณูปโภค",
                    "account": [
                        "5104020000",
                        "5104020008",
                        "5104020099",
                        "5104020003",
                        "5104020005",
                        "5104020006",
                        "5104020001",
                    ],
                },
            ],
        },
        {
            "name": "exp_53000",
            "description": "3. งบลงทุน",
            "children": [
                {
                    "name": "exp_5411000000",
                    "description": "ค่าสิ่งก่อสร้าง",
                    "account": [
                        "5411000000",
                        "5411000005",
                        "5104030207",
                        "5104030209",
                        "5411000004",
                        "5104030208",
                        "5411000003",
                        "5411000001",
                        "5411000002",
                        "5411000009",
                    ],
                },
                {
                    "name": "exp_5412000000",
                    "description": "ค่าครุภัณฑ์",
                    "account": [
                        "5412000000",
                        "5412000002",
                        "5412000014",
                        "5412000015",
                        "5412000011",
                        "5412000010",
                        "5412000009",
                        "5412000007",
                        "5412000018",
                        "5412000017",
                        "5412000016",
                        "5412000001",
                        "5412000013",
                        "5412000003",
                        "5412000004",
                        "5412000005",
                        "5412000006",
                        "5412000008",
                        "5412000026",
                        "5412000012",
                    ],
                },
            ],
        },
        {
            "name": "exp_54000",
            "description": "4. งบเงินอุดหนุน",
            "account": [
                "54100",
                "5107010000",
                "5107010903",
                "5107010291",
                "5107010292",
                "5107010015",
                "5107010044",
                "5107010045",
                "5107010047",
                "5107010048",
                "5107010049",
                "5107010054",
                "5107010022",
                "5107010902",
                "5107010904",
                "5107030004",
                "5107030005",
                "5107010068",
                "5107010069",
                "5107010200",
                "5107010201",
                "5107010202",
                "5107010231",
                "5107010061",
                "5107010065",
                "5107010203",
                "5107010211",
                "5107010221",
                "5107010222",
                "5107010241",
                "5107010251",
                "5107010261",
                "5107010271",
                "5107010281",
                "5107010282",
                "5107010294",
                "5107010295",
                "5107010021",
                "5107010089",
                "5107010091",
                "5107010092",
                "5107010094",
                "5107010801",
                "5107010802",
                "5107010803",
                "5107030003",
                "5107010001",
                "5107010002",
                "5107010003",
                "5107010004",
                "5107010005",
                "5107010006",
                "5107010010",
                "5107010905",
                "5107010906",
                "5107010907",
                "5107010908",
                "5107010059",
                "5107010060",
                "5107010062",
                "5107010804",
                "5107010805",
                "5107010066",
                "5107010067",
                "5107010088",
                "5107010806",
                "5107010807",
                "5107010901",
                "5107010103",
                "5107010102",
                "5107010101",
                "5107010400",
                "5107010106",
                "5107010104",
                "5107010403",
                "5107010402",
                "5107010401",
                "5107010500",
                "5107010502",
                "5107010503",
                "5107010600",
                "5107010501",
                "5107010700",
                "5107010602",
                "5107010601",
                "5107010603",
                "5107010703",
                "5107010702",
                "5107010701",
                "5111000100",
                "5111000105",
                "5111000106",
                "5111000101",
                "5111000102",
                "5111000103",
                "5111000104",
            ],
        },
        {
            "name": "exp_54000",
            "description": "5. งบรายจ่ายอื่น",
            "account": [
                "55100",
                "5108000000",
                "5108000023",
                "5108010103",
                "5108010102",
                "5108000038",
                "5108000037",
                "5108000036",
                "5108000001",
                "5108000002",
                "5108000032",
                "5108000031",
                "5108000025",
                "5108000008",
                "5108000007",
                "5108000029",
                "5108000009",
                "5108000004",
                "5108000022",
                "5108000020",
                "5108000005",
                "5108000006",
                "5108000019",
                "5108000018",
                "5108000017",
                "5108000014",
                "5108000013",
                "5108000012",
                "5108000011",
                "5108000010",
                "5108000003",
                "5109000000",
                "5108000024",
                "5109100016",
                "5109100003",
                "5109100001",
                "5109100010",
                "5109100009",
                "5109100008",
                "5109000004",
                "5109000002",
            ],
        },
        {
            "name": "exp_0702",
            "description": "6. กองทุนสำรอง",
            "account": ["e702", "702"],
        },
    ]

    # level 3
    activities = [
        {"name": "09007", "description": "แผนงานจัดการศึกษาอุดมศึกษา"},
        {"name": "09010", "description": "แผนงานบริการวิชาการแก่สังคม"},
    ]

    # level 4
    funds = [
        ["0100", "กองทุนทั่วไป"],
        ["0200", "กองทุนเพื่อการศึกษา"],
        ["0300", "กองทุนวิจัย"],
        ["0400", "กองทุนบริการวิชาการ"],
        ["0500", "กองทุนกิจการนักศึกษา"],
        ["0600", "กองทุนสินทรัพย์ถาวร"],
        ["0700", "กองทุนอื่น"],
        ["0701", "กองทุนอื่น / กองทุนทำนุบำรุงศิลปวัฒนธรรม"],
        ["0702", "กองทุนอื่น / กองทุนสำรอง"],
        ["0703", "กองทุนอื่น / กองทุนพัฒนาบุคลากร"],
        ["0704", "กองทุนอื่น / กองทุนบูรณาการ"],
        ["0705", "กองทุนอื่น / กองทุนยุทธศาสตร์"],
    ]

    def heading1(self):
        return self.env.ref("mis_budget_kmitl.mis_report_style_f3_p_003_heading_1").id

    def heading2(self):
        return self.env.ref("mis_budget_kmitl.mis_report_style_f3_p_003_heading_2").id

    def heading3(self):
        return self.env.ref("mis_budget_kmitl.mis_report_style_f3_p_003_heading_3").id

    def heading4(self):
        return self.env.ref("mis_budget_kmitl.mis_report_style_f3_p_003_heading_4").id

    def _generate_mis_report_template(self, template_id):
        report_name = "F3-P-วง-003"
        template = self.env["budget.template"].browse(template_id)
        report = self._find_or_create_report()

        items = self.get_revenues() + [self._get_spacing()] + self.get_expenses()

        sequence = 1
        for item in items:
            item["sequence"] = sequence
            sequence += 1

        vals = {"kpi_ids": [Command.clear()] + [Command.create(vals) for vals in items]}
        report.write(vals)

    def _find_or_create_report(self):
        report_name = "F3-P-วง-003"
        report = self.env["mis.report"].search([("name", "=", report_name)], limit=1)

        if not report:
            move_lines_source = (
                self.env["ir.model"]
                .sudo()
                .search([("model", "=", "budget.appropriation.line")], limit=1)
            )
            report = self.env["mis.report"].create(
                {
                    "name": report_name,
                    "description": "สรุปประมาณการรายรับ-รายจ่าย ประจำปีงบประมาณ (ภาพรวม)",
                    "move_lines_source": move_lines_source.id,
                }
            )
        return report

    def get_revenues(self):
        items = []
        for item in self.revenues:
            if item.get("line_type", "num") == "str":
                items.append(self._get_line_str(item))
            if item.get("children"):
                expression = " + ".join(map(lambda i: i["name"], item.get("children")))
                items.append(
                    {
                        "name": item["name"],
                        "description": item["description"],
                        "style_id": self.heading1(),
                        "expression": expression,
                        "type": "num",
                    }
                )
                for child in item.get("children"):
                    items.append(
                        {
                            "name": child["name"],
                            "description": child["description"],
                            "style_id": self.heading2(),
                            "expression": "balp[%(account)s]"
                            % {"account": ",".join(child["account"])},
                            "type": "num",
                        }
                    )
        return items

    def get_expenses(self):
        items = []
        for item in self.expenses:
            if item.get("line_type", "num") == "str":
                items.append(self._get_line_str(item))
                continue
            elif item.get("children"):
                expression = " + ".join(map(lambda i: i["name"], item.get("children")))
                data = {
                    "name": item["name"],
                    "description": item["description"],
                    "style_id": self.heading1(),
                    "expression": expression,
                    "type": "num",
                }

                items.append(data)
                for child in item.get("children"):
                    name = child["name"]
                    account = ",".join(child["account"])
                    expression = "+".join(
                        map(lambda i: name + "_" + i["name"], self.activities)
                    )
                    items.append(
                        {
                            "name": name,
                            "description": child["description"],
                            "style_id": self.heading2(),
                            "expression": expression,
                            "type": "num",
                        }
                    )

                    for activity in self.activities:
                        name = child["name"] + "_" + activity["name"]
                        expression = "+".join(
                            map(lambda i: name + "_" + i[0], self.funds)
                        )
                        items.append(
                            {
                                "name": name,
                                "description": activity["description"],
                                "style_id": self.heading3(),
                                "expression": expression,
                                "type": "num",
                            }
                        )

                        for fund in self.funds:
                            name = "_".join([child["name"], activity["name"], fund[0]])
                            items.append(
                                {
                                    "name": name,
                                    "description": fund[1],
                                    "style_id": self.heading4(),
                                    "expression": "balp[%(account)s]['&', ('activity_analytic_id.code', '=like', '%(activity_analytic_code)s'), ('fund_analytic_id.code', '=', '%(fund_analytic_code)s')]"
                                    % {
                                        "account": account,
                                        "activity_analytic_code": activity["name"]
                                        + "%",
                                        "fund_analytic_code": fund[0],
                                    },
                                    "type": "num",
                                }
                            )
            elif item.get("code") in ["e702", "702"]:
                name = item["name"]
                expression = "+".join(
                    map(lambda i: name + "_" + i["name"], self.activities)
                )
                items.append(
                    {
                        "name": item["name"],
                        "description": item["description"],
                        "style_id": self.heading1(),
                        "expression": expression,
                        "type": "num",
                    }
                )

                for activity in self.activities:
                    name = item["name"] + "_" + activity["name"]
                    expression = "+".join(map(lambda i: name + "_" + i[0], self.funds))
                    items.append(
                        {
                            "name": name,
                            "description": activity["description"],
                            "style_id": self.heading3(),
                            "expression": expression,
                            "type": "num",
                        }
                    )
            elif item.get("account"):
                name = item["name"]
                expression = "+".join(
                    map(lambda i: name + "_" + i["name"], self.activities)
                )
                items.append(
                    {
                        "name": item["name"],
                        "description": item["description"],
                        "style_id": self.heading1(),
                        "expression": expression,
                        "type": "num",
                    }
                )

                for activity in self.activities:
                    name = item["name"] + "_" + activity["name"]
                    expression = "+".join(map(lambda i: name + "_" + i[0], self.funds))
                    items.append(
                        {
                            "name": name,
                            "description": activity["description"],
                            "style_id": self.heading3(),
                            "expression": expression,
                            "type": "num",
                        }
                    )

                    for fund in self.funds:
                        name = item["name"] + "_" + activity["name"] + "_" + fund[0]
                        items.append(
                            {
                                "name": name,
                                "description": fund[1],
                                "style_id": self.heading4(),
                                "expression": "balp[%(account)s]['&', ('activity_analytic_id.code', '=like', '%(activity_analytic_code)s'), ('fund_analytic_id.code', '=', '%(fund_analytic_code)s')]"
                                % {
                                    "account": account,
                                    "activity_analytic_code": activity["name"] + "%",
                                    "fund_analytic_code": fund[0],
                                },
                                "type": "num",
                            }
                        )

        items.append(self._get_total_expense_line())
        return items

    def _get_line_str(self, item):
        return {
            "name": item.get("name"),
            "description": item.get("description"),
            "style_id": self.heading1(),
            "type": "str",
        }

    def _get_spacing(self):
        return {
            "name": "spacing",
            "description": "---",
            "style_id": self.heading1(),
            "type": "str",
        }

    def _get_total_expense_line(self):
        name = "total_expense"
        expression = "+".join(map(lambda i: i["name"], self.expenses))
        return {
            "name": name,
            "description": "รวมทั้งสิ้น",
            "expression": expression,
            "style_id": self.heading3(),
            "type": "num",
        }
