import unittest
from unittest.mock import MagicMock, patch
import json

from form_parser import GoogleFormData, FormQuestion, QuestionType
from gemini_mapper import GeminiFormMapper, FormMappingOutput, MappedQuestionItem
from url_builder import PrefillURLBuilder


class TestGeminiMapper(unittest.TestCase):
    def test_missing_api_key_raises_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError) as ctx:
                GeminiFormMapper(api_key="")
            self.assertIn("Missing Gemini API Key", str(ctx.exception))

    @patch("google.genai.Client")
    def test_successful_mapping(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        # Mock structured response
        sample_response_data = {
            "summary": "Mapped candidate profile to Software Engineer application.",
            "answers": [
                {
                    "entry_id": 1054111098,
                    "question_title": "Full Name",
                    "answer": "Alex Morgan",
                    "is_other": False,
                    "confidence": "HIGH",
                    "reasoning": "Exact match from candidate profile."
                },
                {
                    "entry_id": 1757338475,
                    "question_title": "Gender",
                    "answer": "Male",
                    "is_other": False,
                    "confidence": "HIGH",
                    "reasoning": "Selected from options list based on profile."
                },
                {
                    "entry_id": 140274404,
                    "question_title": "Core Skills",
                    "answer": ["Python", "TypeScript"],
                    "is_other": False,
                    "confidence": "HIGH",
                    "reasoning": "Matches candidate's primary programming languages."
                },
                {
                    "entry_id": 999123456,
                    "question_title": "Why do you want to join us?",
                    "answer": "I am excited to leverage my 5+ years of full-stack experience to help scale your cloud platform.",
                    "is_other": False,
                    "confidence": "MEDIUM",
                    "reasoning": "Synthesized from candidate experience and job description."
                }
            ]
        }

        mock_generate_response = MagicMock()
        mock_generate_response.text = json.dumps(sample_response_data)
        mock_client.models.generate_content.return_value = mock_generate_response

        # Build mock form data
        form_data = GoogleFormData(
            title="Software Engineer Job Application",
            url="https://docs.google.com/forms/d/e/1FAIpQLScSample/viewform",
            questions=[
                FormQuestion(
                    id=1,
                    title="Full Name",
                    question_type=QuestionType.SHORT_ANSWER,
                    entry_id=1054111098,
                    required=True
                ),
                FormQuestion(
                    id=2,
                    title="Gender",
                    question_type=QuestionType.MULTIPLE_CHOICE,
                    entry_id=1757338475,
                    options=["Male", "Female"],
                    required=True
                ),
                FormQuestion(
                    id=3,
                    title="Core Skills",
                    question_type=QuestionType.CHECKBOXES,
                    entry_id=140274404,
                    options=["Python", "TypeScript", "Rust"],
                    required=False
                ),
                FormQuestion(
                    id=4,
                    title="Why do you want to join us?",
                    question_type=QuestionType.PARAGRAPH,
                    entry_id=999123456,
                    required=True
                )
            ]
        )

        mapper = GeminiFormMapper(api_key="test-mock-api-key")
        answers = mapper.map_form(
            form_data=form_data,
            profile_content="Candidate: Alex Morgan, Full-Stack Engineer, 5 years exp.",
            job_description="Looking for Senior Full-Stack Python Engineer."
        )

        self.assertEqual(len(answers), 4)
        self.assertEqual(answers[0].answer, "Alex Morgan")
        self.assertEqual(answers[0].confidence, "HIGH")
        self.assertEqual(answers[1].answer, "Male")
        self.assertEqual(answers[2].answer, ["Python", "TypeScript"])
        self.assertEqual(answers[3].confidence, "MEDIUM")

        # Verify URL building with mapped answers
        url = PrefillURLBuilder.build_url(form_data.url, answers)
        self.assertIn("entry.1054111098=Alex+Morgan", url)
        self.assertIn("entry.1757338475=Male", url)
        self.assertIn("entry.140274404=Python", url)
        self.assertIn("entry.140274404=TypeScript", url)
        self.assertIn("entry.999123456=", url)


if __name__ == "__main__":
    unittest.main()
