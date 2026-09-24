import json
from typing import List, Union, Optional, Dict, Any
from pydantic import BaseModel, Field

from config import config
from form_parser import FormQuestion, GoogleFormData
from url_builder import QuestionAnswer


class MappedQuestionItem(BaseModel):
    entry_id: int = Field(description="The numeric entry ID for this Google Form question.")
    question_title: str = Field(description="The title of the question.")
    answer: Union[str, List[str]] = Field(
        description="The selected or tailored answer. List of strings for checkboxes, string for others."
    )
    is_other: bool = Field(
        default=False,
        description="True if selecting 'Other' option to supply a custom typed value."
    )
    confidence: str = Field(
        description="Confidence level: HIGH (direct match), MEDIUM (inferred/tailored), or LOW (missing data/guess)."
    )
    reasoning: str = Field(
        description="Brief explanation of how this answer was derived or flagged."
    )


class FormMappingOutput(BaseModel):
    summary: str = Field(description="Brief 1-2 sentence overview of the application mapping.")
    answers: List[MappedQuestionItem] = Field(description="List of mapped answers for each fillable question.")


SYSTEM_INSTRUCTION = """You are an expert AI Job Application Assistant.
Your task is to accurately map a candidate's Master Profile and a Job Description onto a set of Google Form questions.

Guidelines:
1. STRICT ACCURACY ON FACTS: Never invent or hallucinate compensation numbers, contact details, work history, or citizenship. If information is not in the profile, provide the safest reasonable answer and mark confidence as 'LOW'.
2. MULTIPLE CHOICE & DROPDOWN QUESTIONS:
   - Your answer MUST EXACTLY MATCH one of the strings listed in the question's 'options' array.
   - Do NOT modify capitalization or punctuation of options.
   - Only set 'is_other' to true if none of the provided options fit AND 'has_other_option' is true.
3. CHECKBOX QUESTIONS:
   - Provide a list of strings matching the allowed options.
4. DATE QUESTIONS:
   - Format dates strictly as YYYY-MM-DD.
5. TAILORED NARRATIVES (e.g. 'Why do you want to join us?', 'Tell us about a project', 'Why hire you?'):
   - Synthesize the candidate's actual projects, achievements, and skills from the Master Profile with the specific mission, technologies, and requirements mentioned in the Job Description.
   - Keep answers authentic, concise, compelling, and free of generic AI fluff.
6. SALARY & CTC:
   - Use numbers specified in the Master Profile. If a range is given and the form asks for a single number, use the expected figure from the profile.
7. CONFIDENCE & REASONING:
   - HIGH: Direct, unambiguous fact from the profile.
   - MEDIUM: Thoughtfully inferred or tailored free-text answer based on real profile data.
   - LOW: Missing information from profile, or forced compromise. Clearly explain why in 'reasoning'.
"""


class GeminiFormMapper:
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key if api_key is not None else config.GEMINI_API_KEY
        self.model_name = model_name or config.GEMINI_MODEL

        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            raise ValueError(
                "Missing Gemini API Key!\n"
                "Please set GEMINI_API_KEY in your .env file or environment variables.\n"
                "You can generate a free API key at: https://aistudio.google.com/"
            )

        # Lazy import of google-genai to ensure clean error messages if SDK is missing
        try:
            from google import genai
            from google.genai import types
            self.genai = genai
            self.types = types
            self.client = genai.Client(api_key=self.api_key)
        except ImportError as e:
            raise ImportError(
                f"Failed to import google-genai SDK: {e}.\n"
                "Please run: pip install -r requirements.txt"
            )

    def map_form(
        self,
        form_data: GoogleFormData,
        profile_content: str,
        job_description: Optional[str] = None,
        additional_notes: Optional[str] = None,
    ) -> List[QuestionAnswer]:
        """
        Calls Gemini API with structured schema to map master profile to form questions.
        """
        fillable_questions = form_data.fillable_questions
        if not fillable_questions:
            return []

        # Prepare questions payload for prompt
        questions_payload = []
        for q in fillable_questions:
            questions_payload.append({
                "entry_id": q.entry_id,
                "title": q.title,
                "description": q.description,
                "question_type": q.question_type.value,
                "required": q.required,
                "options": q.options,
                "has_other_option": q.has_other_option,
            })

        user_prompt = f"""### CANDIDATE MASTER PROFILE:
{profile_content}

### TARGET JOB DESCRIPTION:
{job_description or "No specific job description provided. Map profile directly to the form fields."}

### CANDIDATE ADDITIONAL NOTES:
{additional_notes or "None provided."}

### FORM QUESTIONS TO MAP:
{json.dumps(questions_payload, indent=2)}

Please map the candidate's profile to every question above following all instructions.
"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=self.types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=FormMappingOutput,
                    temperature=0.2,
                ),
            )
        except Exception as e:
            # If the specific model failed, try a fallback common model name
            fallback_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
            alt_model = next((m for m in fallback_models if m != self.model_name), None)
            if alt_model:
                try:
                    response = self.client.models.generate_content(
                        model=alt_model,
                        contents=user_prompt,
                        config=self.types.GenerateContentConfig(
                            system_instruction=SYSTEM_INSTRUCTION,
                            response_mime_type="application/json",
                            response_schema=FormMappingOutput,
                            temperature=0.2,
                        ),
                    )
                except Exception:
                    raise e
            else:
                raise e

        # Extract structured data
        raw_text = response.text
        try:
            parsed_dict = json.loads(raw_text)
            mapping_output = FormMappingOutput(**parsed_dict)
        except Exception as err:
            raise ValueError(f"Failed to parse Gemini response as FormMappingOutput: {err}\nResponse text: {raw_text}")

        # Convert to QuestionAnswer objects
        result_answers: List[QuestionAnswer] = []
        for item in mapping_output.answers:
            result_answers.append(
                QuestionAnswer(
                    entry_id=item.entry_id,
                    question_title=item.question_title,
                    answer=item.answer,
                    is_other=item.is_other,
                    confidence=item.confidence.upper(),
                    reasoning=item.reasoning,
                )
            )

        return result_answers
