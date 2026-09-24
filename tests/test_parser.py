import unittest
from form_parser import GoogleFormParser, QuestionType, GoogleFormData
from url_builder import PrefillURLBuilder, QuestionAnswer


# Realistic snippet of Google Forms internal FB_PUBLIC_LOAD_DATA_
MOCK_RAW_DATA = [
    None,
    [
        "Please fill out this form to apply for the position.",  # Form description
        [
            # Question 0: Short Text (Full Name)
            [
                1051438389,
                "Full Name",
                "Enter your official full name",
                0,  # Type 0: Short Answer
                [[1054111098, None, 1]],  # entry_id=1054111098, required=1
            ],
            # Question 1: Multiple Choice (Gender)
            [
                1051438390,
                "Gender",
                None,
                2,  # Type 2: Multiple Choice
                [
                    [
                        1757338475,
                        [
                            ["Male", None, None, None, 0],
                            ["Female", None, None, None, 0],
                            ["Other", None, None, None, 1],  # other_option = 1
                        ],
                        1,  # required=1
                    ]
                ],
            ],
            # Question 2: Checkboxes (Skills)
            [
                1051438391,
                "Core Skills",
                None,
                4,  # Type 4: Checkboxes
                [
                    [
                        140274404,
                        [
                            ["Python", None, None, None, 0],
                            ["TypeScript", None, None, None, 0],
                            ["Cloud/DevOps", None, None, None, 0],
                        ],
                        0,  # optional
                    ]
                ],
            ],
            # Question 3: Date (Available Start Date)
            [
                1051438392,
                "Start Date",
                None,
                9,  # Type 9: Date
                [[1289670713, None, 1]],
            ],
            # Question 4: File Upload (Resume)
            [
                1051438393,
                "Upload Resume (PDF)",
                "Attach your latest resume",
                13,  # Type 13: File Upload
                [[999999999, None, 1]],
            ],
        ],
        None,
        None,
        None,
        None,
        None,
        None,
        "Senior Software Engineer Application",  # Form Title at index 8
    ],
]


class TestGoogleFormParser(unittest.TestCase):
    def test_parse_raw_data(self):
        form_data = GoogleFormParser.parse_raw_data(
            MOCK_RAW_DATA,
            base_url="https://docs.google.com/forms/d/e/1FAIpQLScSample/viewform"
        )
        self.assertEqual(form_data.title, "Senior Software Engineer Application")
        self.assertEqual(len(form_data.questions), 5)

        # Q0: Full Name
        q0 = form_data.questions[0]
        self.assertEqual(q0.title, "Full Name")
        self.assertEqual(q0.entry_id, 1054111098)
        self.assertEqual(q0.question_type, QuestionType.SHORT_ANSWER)
        self.assertTrue(q0.required)
        self.assertTrue(q0.is_supported)

        # Q1: Gender
        q1 = form_data.questions[1]
        self.assertEqual(q1.title, "Gender")
        self.assertEqual(q1.question_type, QuestionType.MULTIPLE_CHOICE)
        self.assertEqual(q1.options, ["Male", "Female", "Other"])
        self.assertTrue(q1.has_other_option)

        # Q2: Core Skills
        q2 = form_data.questions[2]
        self.assertEqual(q2.question_type, QuestionType.CHECKBOXES)
        self.assertEqual(q2.options, ["Python", "TypeScript", "Cloud/DevOps"])
        self.assertFalse(q2.required)

        # Q3: Date
        q3 = form_data.questions[3]
        self.assertEqual(q3.question_type, QuestionType.DATE)
        self.assertEqual(q3.entry_id, 1289670713)

        # Q4: File Upload
        q4 = form_data.questions[4]
        self.assertEqual(q4.question_type, QuestionType.FILE_UPLOAD)
        self.assertFalse(q4.is_supported)
        self.assertIsNotNone(q4.unsupported_reason)

        # Filtered lists
        self.assertEqual(len(form_data.fillable_questions), 4)
        self.assertEqual(len(form_data.file_upload_questions), 1)

    def test_extract_fb_public_load_data(self):
        mock_html = (
            "<html><head><script>var a = 1; FB_PUBLIC_LOAD_DATA_ = "
            "[null, [\"desc\", [], null, null, null, null, null, null, \"Sample Form\"]]; </script></head></html>"
        )
        extracted = GoogleFormParser.extract_fb_public_load_data(mock_html)
        self.assertIsInstance(extracted, list)
        self.assertEqual(extracted[1][8], "Sample Form")


class TestPrefillURLBuilder(unittest.TestCase):
    def test_normalize_base_url(self):
        url1 = "https://docs.google.com/forms/d/e/1FAIpQLScSample/viewform?usp=sf_link"
        norm1 = PrefillURLBuilder.normalize_base_url(url1)
        self.assertEqual(norm1, "https://docs.google.com/forms/d/e/1FAIpQLScSample/viewform")

        url2 = "https://docs.google.com/forms/d/e/1FAIpQLScSample/formResponse"
        norm2 = PrefillURLBuilder.normalize_base_url(url2)
        self.assertEqual(norm2, "https://docs.google.com/forms/d/e/1FAIpQLScSample/viewform")

    def test_build_url_simple(self):
        base_url = "https://docs.google.com/forms/d/e/1FAIpQLScSample/viewform"
        answers = [
            QuestionAnswer(
                entry_id=1054111098,
                question_title="Full Name",
                answer="Alex Morgan",
                confidence="HIGH"
            ),
            QuestionAnswer(
                entry_id=1757338475,
                question_title="Gender",
                answer="Male",
                confidence="HIGH"
            ),
            QuestionAnswer(
                entry_id=1289670713,
                question_title="Start Date",
                answer="2026-10-01",
                confidence="HIGH"
            )
        ]

        url = PrefillURLBuilder.build_url(base_url, answers)
        self.assertIn("usp=pp_url", url)
        self.assertIn("entry.1054111098=Alex+Morgan", url)
        self.assertIn("entry.1757338475=Male", url)
        self.assertIn("entry.1289670713=2026-10-01", url)

    def test_build_url_checkboxes_and_other(self):
        base_url = "https://docs.google.com/forms/d/e/1FAIpQLScSample/viewform"
        answers = [
            QuestionAnswer(
                entry_id=140274404,
                question_title="Core Skills",
                answer=["Python", "TypeScript"],
                confidence="HIGH"
            ),
            QuestionAnswer(
                entry_id=1757338475,
                question_title="Gender",
                answer="Custom Non-Binary Identity",
                is_other=True,
                confidence="HIGH"
            )
        ]

        url = PrefillURLBuilder.build_url(base_url, answers)
        self.assertIn("entry.140274404=Python", url)
        self.assertIn("entry.140274404=TypeScript", url)
        self.assertIn("entry.1757338475=__other_option__", url)
        self.assertIn("entry.1757338475.other_option_response=Custom+Non-Binary+Identity", url)


if __name__ == "__main__":
    unittest.main()
