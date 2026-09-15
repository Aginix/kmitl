# -*- coding: utf-8 -*-
"""Tests for the virtual `mine_bucket` field and read_group override."""
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestMineBucketGroupby(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_a = new_test_user(
            cls.env,
            login="mb_ua",
            groups="base.group_user,agx_sarabun.group_sarabun_user",
        )
        cls.manager = new_test_user(
            cls.env,
            login="mb_mgr",
            groups="base.group_user,agx_sarabun.group_sarabun_manager",
        )

        Template = cls.env["sarabun.route.template"]
        # 2 templates owned by user_a (mine, from user_a's perspective).
        cls.a1 = Template.with_user(cls.user_a).create(
            {"name": "A owned 1", "visibility": "personal"}
        )
        cls.a2 = Template.with_user(cls.user_a).create(
            {"name": "A owned 2", "visibility": "personal"}
        )
        # 1 template owned by manager and public (visible to user_a as "others").
        cls.pub = Template.with_user(cls.manager).create(
            {"name": "Public", "visibility": "public"}
        )

        cls.Template = Template

    # ── search operator ──────────────────────────────────────────────────────

    def test_search_mine_returns_own_only(self):
        Model = self.Template.with_user(self.user_a)
        mine = Model.search([("mine_bucket", "=", "mine")])
        self.assertEqual(set(mine.ids), {self.a1.id, self.a2.id})

    def test_search_others_excludes_own(self):
        Model = self.Template.with_user(self.user_a)
        others = Model.search([("mine_bucket", "=", "others")])
        self.assertIn(self.pub.id, others.ids)
        self.assertNotIn(self.a1.id, others.ids)
        self.assertNotIn(self.a2.id, others.ids)

    def test_search_not_equal_mine_returns_others(self):
        Model = self.Template.with_user(self.user_a)
        others = Model.search([("mine_bucket", "!=", "mine")])
        self.assertIn(self.pub.id, others.ids)
        self.assertNotIn(self.a1.id, others.ids)

    # ── read_group: single groupby ───────────────────────────────────────────

    def test_read_group_single_returns_two_buckets(self):
        Model = self.Template.with_user(self.user_a)
        groups = Model.read_group([], ["id"], ["mine_bucket"])
        by_key = {g["mine_bucket"]: g for g in groups}
        self.assertEqual(set(by_key), {"mine", "others"})
        self.assertEqual(by_key["mine"]["_count"], 2)
        # Others may include seed data; assert the public template is counted.
        self.assertGreaterEqual(by_key["others"]["_count"], 1)

    def test_read_group_single_domain_scopes_bucket(self):
        Model = self.Template.with_user(self.user_a)
        groups = Model.read_group([], ["id"], ["mine_bucket"])
        mine = next(g for g in groups if g["mine_bucket"] == "mine")
        ids = Model.search(mine["__domain"]).ids
        self.assertEqual(set(ids), {self.a1.id, self.a2.id})

    # ── read_group: nested groupby ───────────────────────────────────────────

    def test_read_group_nested_carries_both_keys(self):
        Model = self.Template.with_user(self.user_a)
        groups = Model.read_group(
            [], ["id"], ["mine_bucket", "visibility"], lazy=True
        )
        # Every row must have both a bucket tag and a visibility tag.
        for g in groups:
            self.assertIn(g["mine_bucket"], ("mine", "others"))
            self.assertIn("visibility", g)
        # 'mine' buckets must only contain user_a's rows.
        mine_rows = [g for g in groups if g["mine_bucket"] == "mine"]
        mine_ids = set()
        for g in mine_rows:
            mine_ids |= set(Model.search(g["__domain"]).ids)
        self.assertEqual(mine_ids, {self.a1.id, self.a2.id})

    def test_read_group_nested_uses_named_count_key(self):
        Model = self.Template.with_user(self.user_a)
        groups = Model.read_group(
            [], ["id"], ["mine_bucket", "visibility"], lazy=True
        )
        # Lazy + multi-groupby → count key is named after the first groupby.
        for g in groups:
            self.assertIn("mine_bucket_count", g)

    # ── delegation: unrelated groupby untouched ─────────────────────────────

    def test_read_group_delegates_when_mine_bucket_absent(self):
        Model = self.Template.with_user(self.user_a)
        groups = Model.read_group([], ["id"], ["visibility"])
        # Standard shape: one row per visibility key present in the data.
        keys = {g["visibility"] for g in groups}
        self.assertTrue(keys.issubset({"personal", "unit", "public"}))
        for g in groups:
            self.assertNotIn("mine_bucket", g)
