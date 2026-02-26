# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHrPreboarding(TransactionCase):
    """Tests for the hr_recruitment_preboarding module.

    Each test method runs in a savepoint that is rolled back afterwards, so
    preboarding records created inside a test do not affect other tests.
    The applicant fixture is created once in setUpClass and shared.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.applicant = cls.env["hr.applicant"].create(
            {
                "name": "Software Engineer Application",
                "partner_name": "John Doe",
                "email_from": "john.doe@example.com",
            }
        )

    def _make_preboarding(self, **kwargs):
        vals = {"applicant_id": self.applicant.id}
        vals.update(kwargs)
        return self.env["hr.preboarding"].create(vals)

    # ------------------------------------------------------------------
    # Creation and defaults
    # ------------------------------------------------------------------

    def test_creation_defaults(self):
        """New preboarding record has state='draft' and a non-empty token."""
        preboarding = self._make_preboarding()
        self.assertEqual(preboarding.state, "draft")
        self.assertTrue(preboarding.token)

    def test_token_uniqueness(self):
        """Each preboarding record receives a distinct UUID token."""
        p1 = self._make_preboarding()
        p2 = self._make_preboarding()
        self.assertNotEqual(p1.token, p2.token)

    def test_portal_url_contains_token(self):
        """portal_url is computed and embeds the record's token."""
        preboarding = self._make_preboarding()
        self.assertIn(preboarding.token, preboarding.portal_url)
        self.assertIn("/preboarding/", preboarding.portal_url)

    # ------------------------------------------------------------------
    # Default documents
    # ------------------------------------------------------------------

    def test_create_default_documents_count(self):
        """_create_default_documents() creates exactly 7 document checklist lines."""
        preboarding = self._make_preboarding()
        self.assertEqual(len(preboarding.document_ids), 0)
        preboarding._create_default_documents()
        self.assertEqual(len(preboarding.document_ids), 7)

    def test_create_default_documents_all_required(self):
        """All default documents are marked as required."""
        preboarding = self._make_preboarding()
        preboarding._create_default_documents()
        self.assertTrue(all(d.required for d in preboarding.document_ids))

    def test_create_default_documents_all_pending(self):
        """All default documents start with state='pending'."""
        preboarding = self._make_preboarding()
        preboarding._create_default_documents()
        self.assertTrue(
            all(d.state == "pending" for d in preboarding.document_ids)
        )

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def test_action_approve(self):
        """action_approve() transitions state from 'submitted' to 'approved'."""
        preboarding = self._make_preboarding()
        preboarding.write({"state": "submitted"})
        preboarding.action_approve()
        self.assertEqual(preboarding.state, "approved")

    def test_action_reject(self):
        """action_reject() transitions state from 'submitted' to 'rejected'."""
        preboarding = self._make_preboarding()
        preboarding.write({"state": "submitted"})
        preboarding.action_reject()
        self.assertEqual(preboarding.state, "rejected")

    # ------------------------------------------------------------------
    # Create employee
    # ------------------------------------------------------------------

    def test_action_create_employee_uses_preboarding_fields(self):
        """action_create_employee() builds hr.employee from preboarding personal data."""
        preboarding = self._make_preboarding()
        preboarding.write(
            {
                "state": "approved",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "mobile": "0812345678",
                "phone": "021234567",
            }
        )
        result = preboarding.action_create_employee()

        self.assertTrue(preboarding.employee_id)
        employee = preboarding.employee_id
        self.assertEqual(employee.name, "John Doe")
        self.assertEqual(employee.work_email, "john@example.com")
        self.assertEqual(employee.mobile_phone, "0812345678")
        self.assertEqual(employee.private_phone, "021234567")

    def test_action_create_employee_returns_employee_action(self):
        """action_create_employee() returns a window action pointing to the new employee."""
        preboarding = self._make_preboarding()
        preboarding.write({"state": "approved", "first_name": "Jane", "last_name": "Smith"})
        result = preboarding.action_create_employee()

        self.assertEqual(result["type"], "ir.actions.act_window")
        self.assertEqual(result["res_model"], "hr.employee")
        self.assertEqual(result["res_id"], preboarding.employee_id.id)

    def test_action_create_employee_falls_back_to_applicant_name(self):
        """When first/last name are empty, employee name falls back to applicant.partner_name."""
        preboarding = self._make_preboarding()
        preboarding.write({"state": "approved"})
        preboarding.action_create_employee()
        self.assertEqual(
            preboarding.employee_id.name, self.applicant.partner_name
        )

    def test_action_create_employee_sets_job_and_department(self):
        """Employee inherits job_id and department_id from the linked applicant."""
        job = self.env["hr.job"].create({"name": "Test Position"})
        dept = self.env["hr.department"].create({"name": "Test Department"})
        self.applicant.write({"job_id": job.id, "department_id": dept.id})
        preboarding = self._make_preboarding()
        preboarding.write(
            {"state": "approved", "first_name": "John", "last_name": "Doe"}
        )
        preboarding.action_create_employee()

        self.assertEqual(preboarding.employee_id.job_id, job)
        self.assertEqual(preboarding.employee_id.department_id, dept)

    # ------------------------------------------------------------------
    # hr.applicant integration
    # ------------------------------------------------------------------

    def test_preboarding_count_starts_at_zero(self):
        """A fresh applicant with no preboarding records has preboarding_count=0."""
        self.assertEqual(self.applicant.preboarding_count, 0)

    def test_preboarding_count_increments(self):
        """preboarding_count reflects the current number of linked preboarding records."""
        self._make_preboarding()
        self.assertEqual(self.applicant.preboarding_count, 1)
        self._make_preboarding()
        self.assertEqual(self.applicant.preboarding_count, 2)

    def test_action_open_preboarding_creates_record_with_docs(self):
        """action_open_preboarding() creates a preboarding record + default docs when none exists."""
        self.assertEqual(self.applicant.preboarding_count, 0)
        result = self.applicant.action_open_preboarding()

        self.assertEqual(self.applicant.preboarding_count, 1)
        preboarding = self.applicant.preboarding_ids
        self.assertEqual(len(preboarding.document_ids), 7)
        self.assertEqual(result["res_model"], "hr.preboarding")
        self.assertEqual(result["res_id"], preboarding.id)

    def test_action_open_preboarding_returns_existing(self):
        """action_open_preboarding() returns the existing record without creating a duplicate."""
        existing = self._make_preboarding()
        result = self.applicant.action_open_preboarding()

        self.assertEqual(self.applicant.preboarding_count, 1)
        self.assertEqual(result["res_id"], existing.id)

    # ------------------------------------------------------------------
    # Education and Document sub-models
    # ------------------------------------------------------------------

    def test_education_line_creation(self):
        """Education lines are created and linked to the preboarding record."""
        preboarding = self._make_preboarding()
        self.env["hr.preboarding.education"].create(
            {
                "preboarding_id": preboarding.id,
                "degree": "Bachelor of Engineering",
                "institution": "KMITL",
                "field_of_study": "Computer Engineering",
                "graduation_year": "2020",
                "gpa": 3.5,
            }
        )
        self.assertEqual(len(preboarding.education_ids), 1)
        edu = preboarding.education_ids
        self.assertEqual(edu.degree, "Bachelor of Engineering")
        self.assertEqual(edu.institution, "KMITL")
        self.assertAlmostEqual(edu.gpa, 3.5)

    def test_document_state_uploaded(self):
        """A document's state can be changed from 'pending' to 'uploaded'."""
        preboarding = self._make_preboarding()
        preboarding._create_default_documents()
        doc = preboarding.document_ids[0]
        self.assertEqual(doc.state, "pending")
        doc.write({"state": "uploaded"})
        self.assertEqual(doc.state, "uploaded")

    def test_document_cascade_delete(self):
        """Deleting a preboarding record also deletes its document checklist lines."""
        preboarding = self._make_preboarding()
        preboarding._create_default_documents()
        doc_ids = preboarding.document_ids.ids
        preboarding.unlink()
        remaining = self.env["hr.preboarding.document"].search(
            [("id", "in", doc_ids)]
        )
        self.assertFalse(remaining)

    def test_education_cascade_delete(self):
        """Deleting a preboarding record also deletes its education lines."""
        preboarding = self._make_preboarding()
        self.env["hr.preboarding.education"].create(
            {"preboarding_id": preboarding.id, "degree": "Master", "institution": "MIT"}
        )
        edu_ids = preboarding.education_ids.ids
        preboarding.unlink()
        remaining = self.env["hr.preboarding.education"].search(
            [("id", "in", edu_ids)]
        )
        self.assertFalse(remaining)

    # ------------------------------------------------------------------
    # Mail template
    # ------------------------------------------------------------------

    def test_mail_template_exists(self):
        """The preboarding mail template is installed and linked to hr.preboarding."""
        template = self.env.ref(
            "hr_recruitment_preboarding.mail_template_preboarding_link",
            raise_if_not_found=False,
        )
        self.assertTrue(template, "Mail template not found — check data/mail_template.xml")
        self.assertEqual(template.model, "hr.preboarding")
