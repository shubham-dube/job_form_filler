import json
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api import app
from url_builder import QuestionAnswer

MOCK_RAW_DATA = [
    None,
    [
        "Job Application Description",
        [
            [
                1001,
                "Full Name",
                "Enter name",
                0,
                [[2001, None, 1]],
            ],
            [
                1002,
                "Resume Upload",
                "Attach PDF",
                13,  # File upload
                [[2002, None, 1]],
            ]
        ],
        None,
        None,
        None,
        None,
        None,
        None,
        "Software Engineer Application"
    ]
]


class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("gemini_model", data)
        self.assertTrue(data["profile_configured"])

    def test_get_profile(self):
        response = self.client.get("/api/profile")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("content", data)
        self.assertIn("path", data)
        self.assertGreater(data["length"], 0)

    def test_parse_form_with_fb_data(self):
        response = self.client.post("/api/parse", json={
            "url": "https://docs.google.com/forms/d/e/test/viewform",
            "fb_data": MOCK_RAW_DATA
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], "Software Engineer Application")
        self.assertEqual(data["stats"]["total"], 2)
        self.assertEqual(data["stats"]["fillable"], 1)
        self.assertEqual(data["stats"]["file_uploads"], 1)

    def test_parse_missing_params_fails(self):
        response = self.client.post("/api/parse", json={})
        self.assertEqual(response.status_code, 400)

    @patch("gemini_mapper.GeminiFormMapper.map_form")
    def test_fill_form_success(self, mock_map_form):
        mock_map_form.return_value = [
            QuestionAnswer(
                entry_id=2001,
                question_title="Full Name",
                answer="Jane Doe",
                confidence="HIGH",
                reasoning="Exact name from profile"
            )
        ]

        response = self.client.post("/api/fill", json={
            "url": "https://docs.google.com/forms/d/e/test/viewform",
            "fb_data": MOCK_RAW_DATA,
            "job_description": "We need a full-stack engineer."
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("entry.2001=Jane+Doe", data["prefilled_url"])
        self.assertEqual(len(data["answers"]), 1)
        self.assertEqual(data["file_upload_questions"], ["Resume Upload"])

    def test_history_flow(self):
        get_res = self.client.get("/api/history")
        self.assertEqual(get_res.status_code, 200)
        self.assertIn("history", get_res.json())

    def test_web_dashboard_pages(self):
        res1 = self.client.get("/")
        self.assertEqual(res1.status_code, 200)
        self.assertIn("FormFiller", res1.text)

        res2 = self.client.get("/dashboard")
        self.assertEqual(res2.status_code, 200)
        self.assertIn("FormFiller", res2.text)


if __name__ == "__main__":
    unittest.main()
