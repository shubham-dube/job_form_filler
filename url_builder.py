import urllib.parse
from typing import List, Union, Dict, Any, Optional
from pydantic import BaseModel


class QuestionAnswer(BaseModel):
    entry_id: int
    question_title: str
    answer: Union[str, List[str]]
    is_other: bool = False
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW
    reasoning: Optional[str] = None


class PrefillURLBuilder:
    @staticmethod
    def normalize_base_url(url: str) -> str:
        """Standardizes Google Form URL to the /viewform endpoint."""
        url = url.strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"

        # Clean query parameters from base URL if present
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        if "/formResponse" in path:
            path = path.replace("/formResponse", "/viewform")
        elif not path.endswith("/viewform"):
            path = path.rstrip("/") + "/viewform"

        # Reconstruct base URL without old query params
        return urllib.parse.urlunparse((
            parsed.scheme,
            parsed.netloc,
            path,
            "",
            "",
            ""
        ))

    @classmethod
    def build_url(cls, base_url: str, answers: List[QuestionAnswer]) -> str:
        """
        Builds the sanctioned Google Forms pre-filled URL.
        Parameters:
        - base_url: Google Form viewform URL
        - answers: List of QuestionAnswer objects
        Returns:
        - Complete pre-filled URL string
        """
        clean_base = cls.normalize_base_url(base_url)
        query_pairs: List[tuple[str, str]] = []

        # Add Google's prefill indicator parameter
        query_pairs.append(("usp", "pp_url"))

        for ans in answers:
            if not ans.entry_id:
                continue

            entry_param = f"entry.{ans.entry_id}"
            
            # Skip empty answers
            if ans.answer is None or ans.answer == "" or ans.answer == []:
                continue

            # Handle Checkbox lists
            if isinstance(ans.answer, list):
                for item in ans.answer:
                    item_str = str(item).strip()
                    if not item_str:
                        continue
                    if ans.is_other and item_str.startswith("__other__:"):
                        custom_text = item_str.replace("__other__:", "").strip()
                        query_pairs.append((entry_param, "__other_option__"))
                        query_pairs.append((f"{entry_param}.other_option_response", custom_text))
                    else:
                        query_pairs.append((entry_param, item_str))
            else:
                answer_str = str(ans.answer).strip()
                if not answer_str:
                    continue

                if ans.is_other:
                    query_pairs.append((entry_param, "__other_option__"))
                    query_pairs.append((f"{entry_param}.other_option_response", answer_str))
                else:
                    query_pairs.append((entry_param, answer_str))

        # Encode query string safely
        query_string = urllib.parse.urlencode(query_pairs)
        prefilled_url = f"{clean_base}?{query_string}"

        return prefilled_url
