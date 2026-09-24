import re
import json
import urllib.request
import urllib.parse
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    SHORT_ANSWER = "short_answer"         # Type 0
    PARAGRAPH = "paragraph"               # Type 1
    MULTIPLE_CHOICE = "multiple_choice"   # Type 2
    DROPDOWN = "dropdown"                 # Type 3
    CHECKBOXES = "checkboxes"             # Type 4
    LINEAR_SCALE = "linear_scale"         # Type 5
    GRID = "grid"                         # Type 7
    SECTION_HEADER = "section_header"     # Type 8
    DATE = "date"                         # Type 9
    TIME = "time"                         # Type 10
    FILE_UPLOAD = "file_upload"           # Type 13
    UNKNOWN = "unknown"


TYPE_CODE_MAP = {
    0: QuestionType.SHORT_ANSWER,
    1: QuestionType.PARAGRAPH,
    2: QuestionType.MULTIPLE_CHOICE,
    3: QuestionType.DROPDOWN,
    4: QuestionType.CHECKBOXES,
    5: QuestionType.LINEAR_SCALE,
    7: QuestionType.GRID,
    8: QuestionType.SECTION_HEADER,
    9: QuestionType.DATE,
    10: QuestionType.TIME,
    13: QuestionType.FILE_UPLOAD,
}


class FormQuestion(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    question_type: QuestionType
    entry_id: Optional[int] = None
    required: bool = False
    options: List[str] = Field(default_factory=list)
    has_other_option: bool = False
    is_supported: bool = True
    unsupported_reason: Optional[str] = None

    @property
    def entry_param_name(self) -> Optional[str]:
        if self.entry_id:
            return f"entry.{self.entry_id}"
        return None


class GoogleFormData(BaseModel):
    title: str
    description: Optional[str] = None
    url: str
    questions: List[FormQuestion] = Field(default_factory=list)

    @property
    def fillable_questions(self) -> List[FormQuestion]:
        return [q for q in self.questions if q.is_supported and q.entry_id is not None]

    @property
    def file_upload_questions(self) -> List[FormQuestion]:
        return [q for q in self.questions if q.question_type == QuestionType.FILE_UPLOAD]


class GoogleSignInRequiredError(Exception):
    """Raised when Google redirects form requests to Google Accounts Sign-In."""
    def __init__(self, url: str, redirect_url: str):
        super().__init__(
            f"Google Form requires Google Sign-in.\n"
            f"Target URL: {url}\n"
            f"Redirected to: {redirect_url}\n\n"
            f"Reason: This form likely contains a File Upload (resume) question or enforces 'Limit to 1 response'.\n"
            f"Solution:\n"
            f"  1. Open the form in your browser, press Ctrl+U (View Source) or Ctrl+S, save it as 'form.html',\n"
            f"     and run the tool with '--html form.html'.\n"
            f"  2. Or provide your session cookies in .env (GOOGLE_COOKIES=...) or with '--cookies'."
        )
        self.url = url
        self.redirect_url = redirect_url


class GoogleFormParser:
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    @classmethod
    def normalize_url(cls, raw_url: str) -> str:
        """Cleans and standardizes form URLs."""
        url = raw_url.strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"
        return url

    @classmethod
    def fetch_form_html(cls, url: str, cookies: Optional[str] = None, timeout: int = 15) -> tuple[str, str]:
        """
        Fetches the HTML of the Google Form, resolving redirects.
        Returns: (html_content, final_viewform_url)
        Raises: GoogleSignInRequiredError if login is required.
        """
        clean_url = cls.normalize_url(url)
        headers = dict(cls.DEFAULT_HEADERS)
        if cookies:
            headers["Cookie"] = cookies

        # Custom HTTP redirect handler to catch login redirects
        class RedirectDetector(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, hdrs, newurl):
                if "accounts.google.com" in newurl:
                    raise GoogleSignInRequiredError(url=clean_url, redirect_url=newurl)
                return super().redirect_request(req, fp, code, msg, hdrs, newurl)

        opener = urllib.request.build_opener(RedirectDetector())
        req = urllib.request.Request(clean_url, headers=headers)

        try:
            with opener.open(req, timeout=timeout) as response:
                final_url = response.geturl()
                content = response.read().decode("utf-8", errors="replace")
                
                # Check for sign-in page even if returned with status 200
                if "accounts.google.com" in final_url or "<title>Google Forms: Sign-in</title>" in content:
                    raise GoogleSignInRequiredError(url=clean_url, redirect_url=final_url)
                
                return content, final_url
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308):
                loc = e.headers.get("Location", "")
                if "accounts.google.com" in loc:
                    raise GoogleSignInRequiredError(url=clean_url, redirect_url=loc)
            elif e.code in (401, 403):
                raise GoogleSignInRequiredError(url=clean_url, redirect_url="https://accounts.google.com/ServiceLogin")
            raise

    @classmethod
    def extract_fb_public_load_data(cls, html: str) -> Any:
        """Extracts and parses the embedded FB_PUBLIC_LOAD_DATA_ JSON blob."""
        pattern = r"FB_PUBLIC_LOAD_DATA_\s*=\s*(.*?);\s*</script>"
        match = re.search(pattern, html, re.DOTALL)
        if not match:
            # Fallback pattern without script closing tag
            pattern2 = r"FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\])\s*;"
            match = re.search(pattern2, html, re.DOTALL)
        
        if not match:
            raise ValueError(
                "Could not find 'FB_PUBLIC_LOAD_DATA_' in the provided HTML. "
                "Ensure this is a valid public Google Form page or saved page source."
            )

        json_str = match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as err:
            raise ValueError(f"Failed to parse Google Forms internal data as JSON: {err}")

    @classmethod
    def parse_html(cls, html: str, base_url: str = "") -> GoogleFormData:
        """Parses Google Form questions and metadata from HTML string."""
        if not base_url:
            # Check for saved from url comment
            url_match = re.search(r"saved from url=\(\d+\)(https?://[^\s>\"']+)", html)
            if url_match:
                base_url = url_match.group(1)
            else:
                url_match2 = re.search(r"(https://docs\.google\.com/forms/d/e/[a-zA-Z0-9_\-]+/viewform)", html)
                if url_match2:
                    base_url = url_match2.group(1)

        raw_data = cls.extract_fb_public_load_data(html)
        return cls.parse_raw_data(raw_data, base_url)

    @classmethod
    def parse_raw_data(cls, raw_data: Any, base_url: str = "") -> GoogleFormData:
        """
        Parses raw FB_PUBLIC_LOAD_DATA_ array into GoogleFormData.
        Standard Google Forms array layout:
        - raw_data[1][8]: Form title
        - raw_data[1][0]: Form description
        - raw_data[1][1]: Questions list
        """
        try:
            meta = raw_data[1]
            title = meta[8] if len(meta) > 8 and meta[8] else "Job Application Form"
            description = meta[0] if len(meta) > 0 and meta[0] else None
            items = meta[1] if len(meta) > 1 and meta[1] else []
        except (IndexError, TypeError) as e:
            raise ValueError(f"Unexpected Google Forms internal data structure: {e}")

        questions: List[FormQuestion] = []

        for item in items:
            if not isinstance(item, list) or len(item) < 4:
                continue

            q_id = item[0]
            q_title = (item[1] or "").strip()
            q_desc = item[2]
            type_code = item[3]
            q_type = TYPE_CODE_MAP.get(type_code, QuestionType.UNKNOWN)

            # Skip section headers from question lists
            if q_type == QuestionType.SECTION_HEADER:
                continue

            # Parse entry details from item[4]
            entry_id = None
            required = False
            options: List[str] = []
            has_other_option = False
            is_supported = True
            unsupported_reason = None

            if q_type == QuestionType.FILE_UPLOAD:
                is_supported = False
                unsupported_reason = (
                    "Google deliberately blocks pre-filling file upload fields via URL. "
                    "Please attach your resume manually in the browser before submitting."
                )

            entry_specs = item[4] if len(item) > 4 else None
            if entry_specs and isinstance(entry_specs, list) and len(entry_specs) > 0:
                sub = entry_specs[0]
                if isinstance(sub, list):
                    # Entry ID is sub[0]
                    if len(sub) > 0 and sub[0] is not None:
                        entry_id = sub[0]

                    # Choices/Options in sub[1]
                    if len(sub) > 1 and isinstance(sub[1], list):
                        for opt in sub[1]:
                            if isinstance(opt, list) and len(opt) > 0:
                                opt_text = opt[0]
                                if opt_text is not None and opt_text != "":
                                    options.append(str(opt_text).strip())
                                # Check for 'other' option flag
                                if len(opt) > 4 and opt[4] == 1:
                                    has_other_option = True

                    # Required flag in sub[2]
                    if len(sub) > 2 and sub[2] == 1:
                        required = True

            question = FormQuestion(
                id=q_id,
                title=q_title,
                description=q_desc,
                question_type=q_type,
                entry_id=entry_id,
                required=required,
                options=options,
                has_other_option=has_other_option,
                is_supported=is_supported,
                unsupported_reason=unsupported_reason,
            )
            questions.append(question)

        # Normalize base URL to .../viewform
        clean_base = base_url
        if clean_base:
            if "/viewform" not in clean_base and "/formResponse" not in clean_base:
                clean_base = clean_base.rstrip("/") + "/viewform"
            elif "/formResponse" in clean_base:
                clean_base = clean_base.replace("/formResponse", "/viewform")

        return GoogleFormData(
            title=title.strip(),
            description=description.strip() if description else None,
            url=clean_base,
            questions=questions,
        )

    @classmethod
    def parse_from_url(cls, url: str, cookies: Optional[str] = None) -> GoogleFormData:
        """Fetches from URL and parses questions."""
        html, final_url = cls.fetch_form_html(url, cookies=cookies)
        return cls.parse_html(html, base_url=final_url)

    @classmethod
    def parse_from_file(cls, file_path: str, base_url: str = "") -> GoogleFormData:
        """Parses questions from a saved HTML file."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            html = f.read()
        return cls.parse_html(html, base_url=base_url)
