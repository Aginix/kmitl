from datetime import date

from odoo.tests.common import tagged

from .common import KrisProjectCommon


@tagged("post_install", "-at_install")
class TestKrisProjectDashboard(KrisProjectCommon):
    """Numeric KPI cards of ``get_dashboard_data``.

    Scope the aggregation with a ``type_id`` filter so the assertions are
    deterministic even when demo projects exist in the database.
    """

    def test_dashboard_cards(self):
        p1 = self._make_project(project_value=1_000_000.0)
        p2 = self._make_project(project_value=500_000.0)
        self.Receipt.create(
            {
                "project_id": p1.id,
                "name": "R1",
                "date": date(2025, 1, 1),
                "amount": 300_000.0,
            }
        )
        self.Receipt.create(
            {
                "project_id": p2.id,
                "name": "R2",
                "date": date(2025, 1, 1),
                "amount": 200_000.0,
            }
        )
        data = self.Project.get_dashboard_data({"type_id": self.ptype.id})
        cards = data["cards"]
        self.assertAlmostEqual(cards["total_estimated"], 1_500_000.0, 2)
        self.assertAlmostEqual(cards["total_received"], 500_000.0, 2)
        # achievement_pct = total_received / total_estimated * 100
        self.assertAlmostEqual(
            cards["achievement_pct"], 500_000.0 / 1_500_000.0 * 100, 2
        )

    def test_dashboard_achievement_zero_guard(self):
        empty_type = self.env["kris.project.type"].create(
            {"name": "Empty Type", "category_id": self.category.id}
        )
        data = self.Project.get_dashboard_data({"type_id": empty_type.id})
        self.assertAlmostEqual(data["cards"]["total_estimated"], 0.0, 2)
        self.assertAlmostEqual(data["cards"]["achievement_pct"], 0.0, 2)
