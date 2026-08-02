"""Create the canonical, validated question bank and extraction report."""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "extraction" / "raw-questions.json"
DATA_PATH = ROOT / "study-website" / "data" / "questions.json"
REPORT_PATH = ROOT / "study-website" / "QUESTION_EXTRACTION_REPORT.md"

SUPPORTED_TYPES = {
    "mcq",
    "multi-select",
    "true-false-group",
    "matching",
    "ordering",
    "source-review",
}

META_LINE = re.compile(
    r"^(?:Page|Pages)\s+\d|^(?:New Test Bank\s*[·•-]?\s*)?Question\s+\d+"
    r"$|^STEM$|^QUESTION\s*&\s*ANSWER(?:\s+Image from question)?$|^\d{1,3}$",
    re.I,
)
CHOICE_MARKER = re.compile(r"^([A-E])\s*[.]?\s*([×✓])(?:\s+(.*))?$")


def normalize(value: str) -> str:
    return " ".join(value.replace("\x00", " ").split())


def duplicate_key(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def clean_lines(entry: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for value in entry.get("rawLines", []):
        line = normalize(value)
        if not line or META_LINE.match(line):
            continue
        line = re.sub(r"\bImage from question\b", "", line, flags=re.I).strip()
        if line:
            lines.append(line)
    return lines


def source_reference(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "collection": entry["sourceId"],
        "file": entry["sourceFile"],
        "page": entry["sourcePage"],
        "question": entry["sourceQuestion"],
    }


def topic_for(text: str) -> str:
    value = text.lower()
    rules = [
        ("Backup and Recovery", ("backup", "restore", "recovery", "file history")),
        ("Networking", ("network", "ipconfig", "wi-fi", "router", "intranet", "extranet")),
        ("Security and Malware", ("malware", "virus", "worm", "phishing", "defender", "biometric")),
        ("Accounts and Permissions", ("account", "permission", "administrator", "group policy", "domain")),
        ("Hardware and Peripherals", ("usb", "hdmi", "displayport", "monitor", "keyboard", "connector")),
        ("Applications and Updates", ("application", "microsoft store", "windows update", "install")),
        ("Cloud Services", ("cloud", "azure", "teams", "sharepoint", "intune", "onedrive")),
        ("Storage and File Systems", ("ntfs", "fat32", "exfat", "disk", "file system")),
        ("Windows Settings", ("settings", "personalization", "accessibility", "ease of access")),
        ("Troubleshooting", ("troubleshoot", "startup", "task manager", "device manager")),
    ]
    for topic, keywords in rules:
        if any(keyword in value for keyword in keywords):
            return topic
    return "General"


def base_question(entry: dict[str, Any], prompt: str) -> dict[str, Any]:
    return {
        "id": "",
        "type": "source-review",
        "prompt": normalize(prompt),
        "topic": topic_for(prompt),
        "options": [],
        "statements": [],
        "items": [],
        "correctAnswer": None,
        "sources": [source_reference(entry)],
        "explanation": "",
        "needsReview": False,
        "reviewNotes": "",
        "sourceImage": "",
    }


def group_correct_mark_lines(entry: dict[str, Any]) -> list[str]:
    marks = [
        mark
        for mark in entry.get("answerMarks", [])
        if mark.get("role") == "correct" and mark.get("text") not in {"✓", "×"}
    ]
    grouped: list[list[str]] = []
    group_y: list[float] = []
    for mark in sorted(marks, key=lambda item: (item["y"], item["x"])):
        if not grouped or abs(float(mark["y"]) - group_y[-1]) > 3:
            grouped.append([])
            group_y.append(float(mark["y"]))
        grouped[-1].append(mark["text"])
    return [normalize(" ".join(words)) for words in grouped if words]


def parse_choice(entry: dict[str, Any], lines: list[str]) -> dict[str, Any] | None:
    marker_indexes = [
        index for index, line in enumerate(lines) if CHOICE_MARKER.match(line)
    ]
    if not marker_indexes:
        return None

    options: list[str] = []
    correct_indexes: list[int] = []
    for position, line_index in enumerate(marker_indexes):
        match = CHOICE_MARKER.match(lines[line_index])
        assert match is not None
        end = marker_indexes[position + 1] if position + 1 < len(marker_indexes) else len(lines)
        option_parts = [match.group(3) or ""] + lines[line_index + 1 : end]
        option = normalize(" ".join(part for part in option_parts if part))
        option = re.sub(r"\s+\d{1,3}$", "", option).strip()
        options.append(option)
        if match.group(2) == "✓":
            correct_indexes.append(position)

    prompt = normalize(" ".join(lines[: marker_indexes[0]]))
    question = base_question(entry, prompt)
    question["options"] = options
    if len(correct_indexes) == 1:
        question["type"] = "mcq"
        question["correctAnswer"] = correct_indexes[0]
    elif len(correct_indexes) > 1:
        question["type"] = "multi-select"
        question["correctAnswer"] = correct_indexes
    else:
        question["needsReview"] = True
        question["reviewNotes"] = "No official check mark was extracted for the choices."

    if len(options) < 3 or any(not option for option in options):
        question["type"] = "source-review"
        question["correctAnswer"] = None
        question["needsReview"] = True
        question["reviewNotes"] = "One or more choices could not be separated reliably."
    return question


def parse_group(entry: dict[str, Any], lines: list[str]) -> dict[str, Any] | None:
    value = " ".join(lines).lower()
    if not any(term in value for term in ("true or false", "true false", "truefalse", "yes if")):
        return None

    answer_pattern = re.compile(r"\b(true\s*false|yes\s*no)\b", re.I)
    answer_indexes = [
        index for index, line in enumerate(lines) if answer_pattern.search(line)
    ]
    if not answer_indexes:
        return None

    first_answer = answer_indexes[0]
    boundary_candidates = [
        index
        for index, line in enumerate(lines[: first_answer + 1])
        if (
            "partial credit" in line.lower()
            or "select true or false" in line.lower()
            or "select yes if" in line.lower()
            or "select yes or no" in line.lower()
        )
        and not (
            index == first_answer
            and normalize(answer_pattern.sub("", line))
        )
    ]
    statement_start = (
        boundary_candidates[-1] + 1
        if boundary_candidates
        else max(0, first_answer - 1)
    )
    while statement_start < first_answer and lines[statement_start].lower() in {
        "correctly", "response.", "selection.", "correct response."
    }:
        statement_start += 1

    statements: list[str] = []
    segment_start = statement_start
    for answer_index in answer_indexes:
        segment = lines[segment_start : answer_index + 1]
        cleaned_parts = [normalize(answer_pattern.sub("", line)) for line in segment]
        statement = normalize(" ".join(part for part in cleaned_parts if part))
        statement = re.sub(
            r"^(?:(?:note[.:]?\s*)?(?:you|wii)\s+will\s+receive\s+"
            r"(?:part|partial)\s+credit\s+for\s+each\s+correct\s+selection\s+"
            r"|selection\s+|response\s+|answer\s+)",
            "",
            statement,
            flags=re.I,
        ).strip()
        if statement:
            statements.append(statement)
        segment_start = answer_index + 1

    correct_marks = [
        mark
        for mark in sorted(entry.get("answerMarks", []), key=lambda item: (item["y"], item["x"]))
        if mark.get("role") == "correct"
        and mark.get("text", "").lower() in {"true", "false", "yes", "no"}
    ]
    correct = [mark["text"].lower() in {"true", "yes"} for mark in correct_marks]
    prompt = normalize(" ".join(lines[:statement_start]))
    question = base_question(entry, prompt)
    question["type"] = "true-false-group"
    question["statements"] = statements
    question["answerLabels"] = ["True", "False"] if "yes if" not in value else ["Yes", "No"]
    question["correctAnswer"] = correct
    if not statements or len(statements) != len(correct):
        question["type"] = "source-review"
        question["correctAnswer"] = None
        question["needsReview"] = True
        question["reviewNotes"] = (
            f"Statement/answer count mismatch ({len(statements)} statements, "
            f"{len(correct)} official answers)."
        )
    return question


def matching_question(
    entry: dict[str, Any],
    prompt: str,
    pairs: list[tuple[str, str]],
) -> dict[str, Any]:
    question = base_question(entry, prompt)
    question["type"] = "matching"
    question["items"] = [
        {"id": f"item-{index + 1}", "text": item}
        for index, (item, _answer) in enumerate(pairs)
    ]
    question["options"] = list(dict.fromkeys(answer for _item, answer in pairs))
    question["correctAnswer"] = {
        f"item-{index + 1}": answer
        for index, (_item, answer) in enumerate(pairs)
    }
    return question


def manual_override(entry: dict[str, Any], lines: list[str]) -> dict[str, Any] | None:
    page = entry["sourcePage"]
    prompt = normalize(" ".join(lines))
    settings_options = [
        "System", "Devices", "Phone", "Network & Internet", "Personalization",
        "Apps", "Accounts", "Time & Language", "Gaming", "Ease of Access",
        "Search", "Privacy", "Update & Security",
    ]

    if page in {5, 42, 58}:
        question = base_question(entry, prompt)
        question["type"] = "mcq"
        question["options"] = settings_options
        answer = "Personalization" if page == 42 else "Ease of Access"
        question["correctAnswer"] = settings_options.index(answer)
        question["sourceImage"] = f"./assets/source-pages/bank-page-{page}.jpg"
        return question
    if page == 8:
        return matching_question(entry, prompt, [
            ("A backup of all data on the drive at a given time", "Full"),
            ("A backup of all data created or changed since the last backup", "Incremental"),
            ("A backup of all data created or changed since the last full backup", "Differential"),
            ("A backup that automatically updates as data changes on the drive", "Mirror"),
        ])
    if page == 9:
        question = base_question(entry, prompt)
        question["type"] = "ordering"
        question["items"] = [
            "Local group policy", "Site group policy",
            "Domain group policy", "organization group policy",
        ]
        question["correctAnswer"] = list(question["items"])
        return question
    if page == 11:
        return matching_question(entry, prompt, [
            ("DisplayPort", "Audio and video"),
            ("DVI", "Video"),
            ("HDMI", "Audio and video"),
            ("USB-C", "Audio and video"),
            ("VGA", "Video"),
        ])
    if page == 16:
        question = matching_question(entry, prompt, [
            ("Information indicating whether the computer can join a domain", "Local administrator"),
            ("Account type required to join the computer to the domain", "Local administrator"),
        ])
        question["sourceImage"] = "./assets/source-pages/bank-page-16.jpg"
        return question
    if page == 19:
        question = matching_question(entry, prompt, [
            ("Recover a backup of a Windows installation and personalized files", "System image recovery"),
            ("Recover from a failed device driver update without losing files", "System restore"),
        ])
        question["sourceImage"] = "./assets/source-pages/bank-page-19.jpg"
        return question
    if page in {21, 80}:
        return matching_question(entry, prompt, [
            ("Delivers both power and data to a device", "USB Type-C"),
            ("Typically found on legacy monitors and computers", "VGA"),
            ("Used by monitors and computers but not game consoles", "DisplayPort"),
            ("Used by televisions, computers, game consoles, and projectors", "HDMI"),
        ])
    if page == 23:
        return matching_question(entry, prompt, [
            ("For each account you must assign a unique …", "username"),
            ("The username will appear with the user's …", "user name and photo"),
            ("The username will appear on the user's …", "Start menu and welcome screen"),
        ])
    if page == 25:
        return matching_question(entry, prompt, [
            ("Guests", "Public network"),
            ("Employees", "Private network"),
            ("Business partners", "Extranet"),
        ])
    if page == 31:
        return matching_question(entry, prompt, [
            ("Turn on built-in Windows features", "Administrator"),
            ("Install Microsoft Store apps", "Standard user"),
            ("Install applications in the Program Files folder", "Administrator"),
        ])
    if page == 38:
        return matching_question(entry, prompt, [
            ("Backup takes the least amount of time to back up data", "Incremental"),
            ("Amount of time to restore all data", "Longest"),
        ])
    if page == 44:
        question = matching_question(entry, prompt, [
            ("Image 1", "DisplayPort"), ("Image 2", "HDMI"), ("Image 3", "VGA"),
        ])
        question["sourceImage"] = "./assets/source-pages/bank-page-44.jpg"
        return question
    if page == 46:
        return matching_question(entry, prompt, [
            ("Tracks a user's computer usage", "spyware"),
            ("Sends copies of itself to other machines", "worm"),
            ("Spreads when a user runs an executable", "virus"),
        ])
    if page == 47:
        return matching_question(entry, prompt, [
            ("Document library", "SharePoint"),
            ("Video calls", "Teams"),
            ("Virtual machines", "Azure"),
        ])
    if page == 51:
        return matching_question(entry, prompt, [
            ("For each account, you must assign a unique …", "username"),
            ("The username will appear on the user's …", "Start menu and Welcome screen"),
        ])
    if page == 53:
        question = base_question(
            entry,
            "For each statement about installing Windows 10, select True or False.",
        )
        question["type"] = "true-false-group"
        question["statements"] = [
            "More than one English language option is available",
            "Installation options include USB or network share",
            "Choosing the Upgrade option overwrites all installed applications and settings",
        ]
        question["answerLabels"] = ["True", "False"]
        question["correctAnswer"] = [True, True, False]
        return question
    if page == 54:
        question = base_question(entry, prompt)
        question["type"] = "mcq"
        question["options"] = [
            "Show only on 2", "Extend desktop to this display",
            "Make this my main display", "Custom scaling",
        ]
        question["correctAnswer"] = 2
        return question
    if page == 55:
        return matching_question(entry, prompt, [
            ("Load only the drivers required for connecting to other computers", "Safe mode with networking"),
            ("Load the most recent drivers and registry settings that worked successfully", "Last known good configuration"),
            ("Create a file containing a list of drivers installed during setup", "Enable boot logging"),
        ])
    if page == 67:
        question = base_question(
            entry,
            "You need to uninstall a Windows update from a computer. Where should you perform this task?",
        )
        question["type"] = "mcq"
        question["options"] = [
            "Windows Update history",
            "Windows Update Advanced Options",
            "Action Center",
            "Windows Security",
        ]
        question["correctAnswer"] = 0
        return question
    if page == 74:
        return matching_question(entry, prompt, [
            ("Network discovery is turned off", "Public"),
            ("Typically used for trusted home or office networks", "Private"),
            ("Used when connecting as a guest without a user account", "Public"),
        ])
    if page == 79:
        question = base_question(entry, "What the the purpose of the Microsoft Store?")
        question["type"] = "mcq"
        question["options"] = [
            "A digital distribution platform and marketplace for Microsoft approved applications",
            "digital distribution platform and marketplace for all applications",
            "An online marketplace for buying Microsoft branded computers and peripherals",
            "An online marketplace for selling and buying used hardware",
        ]
        question["correctAnswer"] = 0
        return question
    if page == 83:
        question = matching_question(entry, prompt, [
            ("Display orientation", "Landscape"),
            ("Display resolution", "1920x1080 (Recommended)"),
            ("Multiple displays", "Extend these displays"),
            ("Size of text, apps, and other items", "100% (Recommended)"),
        ])
        question["sourceImage"] = "./assets/source-pages/bank-page-83.jpg"
        return question
    if page == 84:
        question = base_question(
            entry,
            normalize(" ".join(lines[:-1])),
        )
        question["type"] = "source-review"
        question["correctAnswer"] = "Roll Back Driver"
        question["sourceImage"] = "./assets/source-pages/bank-page-84.jpg"
        return question
    if page == 88:
        question = base_question(
            entry,
            "you are working as a tier I technical support technician tor a company that has 4 tiers of technical support personnel an employee is experiencing an issue that requires specialized knowledge about hardware that is different from the hardware you have been trained on how should you assist the user In resolving their Issue?",
        )
        question["type"] = "mcq"
        question["options"] = [
            "Submit a request to be trained In the unique hardware and software to support the employee",
            "Escalate employee's Issue to a tier 2 technical support technician",
            "Provide employee With phone numbers for the hardware vendor to receive support D. Can the hardware to receive training to help support the employee.",
        ]
        question["correctAnswer"] = 1
        return question
    if page == 90:
        return matching_question(entry, prompt, [
            ("Self-replicating malware", "worm"),
            ("Malware disguised as legitimate software", "Trojan horse"),
            ("Attack that exhausts website or server resources", "DDoS"),
            ("Attack that deceives people into revealing personal information", "Phishing"),
        ])
    if page == 95:
        question = base_question(
            entry,
            normalize(" ".join(lines[:-2])),
        )
        question["type"] = "source-review"
        question["correctAnswer"] = "Click Scan for hardware changes from the Action menu"
        question["sourceImage"] = "./assets/source-pages/bank-page-95.jpg"
        return question
    if page == 100:
        return matching_question(entry, prompt, [
            ("Permission that allows you to create a subfolder", "Write"),
            ("Permission that allows you to delete a subfolder", "Modify"),
            ("Permission that allows you to run an application", "Read & Execute"),
        ])
    if page == 102:
        return matching_question(entry, prompt, [
            ("Collection of cloud-based productivity apps", "Microsoft 365 (Office 365)"),
            ("Works like a binder with tabs separating sections and pages", "OneNote"),
            ("Stores documentation for collaboration across an organization", "SharePoint"),
            ("Runs an operating system accessible from Windows, macOS, or ChromeOS", "Windows 365 Cloud PC"),
        ])
    if page == 106:
        return matching_question(entry, prompt, [
            ("Go to Command Prompt and …", "run ipconfig /renew (or ping the router)"),
            ('If the "No internet" icon is visible, verify …', "Wi-Fi is turned on (or airplane mode is off)"),
            ("You should also try …", "restarting the router (or forgetting and reconnecting to the network)"),
        ])
    return None


def parse_bank_entry(entry: dict[str, Any]) -> dict[str, Any]:
    lines = clean_lines(entry)
    override = manual_override(entry, lines)
    if override:
        return override
    choice = parse_choice(entry, lines)
    if choice:
        return choice
    group = parse_group(entry, lines)
    if group:
        return group

    prompt = normalize(" ".join(lines))
    question = base_question(entry, prompt)
    answers = group_correct_mark_lines(entry)
    if answers:
        question["correctAnswer"] = answers[0] if len(answers) == 1 else answers
    else:
        question["needsReview"] = True
        question["reviewNotes"] = "The official answer could not be extracted reliably."
    if "image from question" in entry["rawText"].lower():
        question["sourceImage"] = (
            f"./assets/source-pages/bank-page-{entry['sourcePage']}.jpg"
        )
    return question


def answer_signature(question: dict[str, Any]) -> str:
    if question["type"] in {"mcq", "multi-select"} and question.get("options"):
        indexes = (
            [question["correctAnswer"]]
            if isinstance(question["correctAnswer"], int)
            else question["correctAnswer"] or []
        )
        values = [
            duplicate_key(question["options"][index])
            for index in indexes
            if isinstance(index, int) and index < len(question["options"])
        ]
        return "|".join(sorted(values))
    return duplicate_key(json.dumps(question["correctAnswer"], sort_keys=True))


def merge_bank_duplicates(
    parsed: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]], int]:
    unique: list[dict[str, Any]] = []
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    by_page: dict[int, dict[str, Any]] = {}
    duplicate_count = 0
    for question in parsed:
        key = (duplicate_key(question["prompt"]), answer_signature(question))
        existing = by_key.get(key)
        if existing and key[0]:
            existing["sources"].extend(question["sources"])
            by_page[question["sources"][0]["page"]] = existing
            duplicate_count += 1
            continue
        question["id"] = f"q-{len(unique) + 1:03d}"
        unique.append(question)
        by_key[key] = question
        by_page[question["sources"][0]["page"]] = question
    return unique, by_page, duplicate_count


STOPWORDS = {
    "page", "pages", "question", "stem", "answer", "area", "pre", "test",
    "exam", "true", "false", "select", "note", "will", "receive", "partial",
    "credit", "correct", "selection", "each",
}


def token_set(value: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2 and token not in STOPWORDS
    }


def similarity(left: str, right: str) -> float:
    a, b = token_set(left), token_set(right)
    return len(a & b) / max(1, len(a | b))


def attach_pretest_sources(
    questions: list[dict[str, Any]],
    bank_entries: list[dict[str, Any]],
    bank_by_page: dict[int, dict[str, Any]],
    pretest_entries: list[dict[str, Any]],
) -> tuple[int, list[str]]:
    conflicts = 0
    notes: list[str] = []
    for entry in pretest_entries:
        number = entry["sourceQuestion"]
        if number == 40:
            question = base_question(
                entry,
                "Complete the sentence by selecting the correct option from each drop-down list.",
            )
            question["id"] = f"q-{len(questions) + 1:03d}"
            question["type"] = "source-review"
            question["needsReview"] = True
            question["correctAnswer"] = None
            question["reviewNotes"] = (
                "Answer conflict: pre-test PDF page 46 highlights Differential, "
                "while the 105-question bank PDF page 38 marks Incremental."
            )
            question["sourceImage"] = "./assets/source-pages/pretest-page-46.jpg"
            questions.append(question)
            conflicts += 1
            notes.append(question["reviewNotes"])
            continue

        if number == 4:
            best_entry = next(item for item in bank_entries if item["sourcePage"] == 5)
            best_score = 1.0
        else:
            best_score, best_entry = max(
                (
                    (similarity(entry["rawText"], candidate["rawText"]), candidate)
                    for candidate in bank_entries
                ),
                key=lambda pair: pair[0],
            )
        target = bank_by_page[best_entry["sourcePage"]]
        target["sources"].append(source_reference(entry))
        target.setdefault("duplicateSources", []).append(
            {
                "collection": "pretest-70",
                "page": entry["sourcePage"],
                "matchScore": round(best_score, 3),
            }
        )
        if best_score < 0.12:
            note = (
                f"Low OCR match confidence for pre-test question {number} "
                f"(page {entry['sourcePage']}) matched to bank page "
                f"{best_entry['sourcePage']}."
            )
            target["reviewNotes"] = normalize(
                " ".join(part for part in [target["reviewNotes"], note] if part)
            )
            notes.append(note)
    return conflicts, notes


def validate_question(question: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if question["type"] not in SUPPORTED_TYPES:
        errors.append(f"unsupported type {question['type']}")
    if not question["prompt"]:
        errors.append("missing prompt")
    if not question["sources"]:
        errors.append("missing source")
    if question["needsReview"]:
        if question["correctAnswer"] is not None:
            errors.append("review item must not contain a guessed answer")
        if not question["reviewNotes"]:
            errors.append("review item needs a review note")
    elif question["correctAnswer"] is None:
        errors.append("missing official answer")
    if question["type"] == "mcq" and not question["needsReview"]:
        if not isinstance(question["correctAnswer"], int):
            errors.append("MCQ answer is not an index")
        elif question["correctAnswer"] >= len(question["options"]):
            errors.append("MCQ answer index is out of range")
    return errors


def create_report(
    questions: list[dict[str, Any]],
    bank_duplicates: int,
    answer_conflicts: int,
    matching_notes: list[str],
) -> str:
    type_counts = Counter(question["type"] for question in questions)
    review_items = [question for question in questions if question["needsReview"]]
    lines = [
        "# Question Extraction Report",
        "",
        "## Source coverage",
        "",
        "- Total PDF pages: 183 (106 + 77)",
        "- Official question source entries: 175 (105 + 70)",
        f"- Canonical unique questions: {len(questions)}",
        f"- Duplicate source entries merged: {175 - len(questions)}",
        f"- Duplicate questions found inside the 105-question bank: {bank_duplicates}",
        f"- Confirmed cross-PDF answer conflicts: {answer_conflicts}",
        "",
        "## Question types",
        "",
    ]
    for question_type in sorted(type_counts):
        lines.append(f"- {question_type}: {type_counts[question_type]}")
    lines.extend([
        "",
        "## Manual review",
        "",
        f"- Questions requiring manual review: {len(review_items)}",
    ])
    for question in review_items:
        source_text = ", ".join(
            f"{source['file']} page {source['page']}" for source in question["sources"]
        )
        lines.append(
            f"- `{question['id']}` — {question['reviewNotes']} Sources: {source_text}"
        )
    lines.extend([
        "",
        "## Arabic study guidance",
        "",
        "- `data/explanations-ar.json` contains 103 generated Arabic translations and study explanations, one for each canonical question.",
        "- The generated guidance is clearly labeled in the site and remains separate from official PDF questions and answers.",
        "- Search covers English prompts plus Arabic translations, explanation paragraphs, and revision notes; source, topic, and type filters can be combined.",
        "- Guidance appears after Practice answers and inside Question Bank and Exam Result review disclosures, but never during an active Mock Exam.",
        "- The guidance does not resolve `q-103`; it describes the conflict and directs learners to pre-test PDF page 46 and 105-question bank PDF page 38.",
        "",
        "## Arabic guidance maintenance",
        "",
        "- Editable entries are split across `content/explanations-ar/q001-026.json`, `content/explanations-ar/q027-052.json`, `content/explanations-ar/q053-078.json`, and `content/explanations-ar/q079-103.json`.",
        "- Run `python scripts/build_explanations.py` from the project root to merge the parts, require exact canonical-ID coverage, validate Arabic fields, and regenerate `study-website/data/explanations-ar.json`.",
        "- Correct guidance in the matching content-part entry without changing the canonical prompt, official answer, or source references.",
        "- Never select an answer for an unresolved official-source conflict. Preserve `needsReview`, the source references, and the unscored behavior.",
    ])
    lines.extend([
        "",
        "## Extraction quality",
        "",
        "- The 105-question PDF was extracted from selectable text.",
        "- Green text/check marks were treated as official correct answers; red text/cross marks were treated as wrong answers.",
        "- The 70-question pre-test contains screenshot-only content and was extracted with rendered-page OCR.",
        "- Red official-answer rectangles were detected on every pre-test question page.",
        "- OCR text was matched to the canonical bank; low-confidence matches remain traceable through their source references.",
        "- No PDF pages failed to render.",
        "",
        "## Formatting corrections",
        "",
        "- Collapsed broken line wrapping and repeated whitespace.",
        "- Preserved source wording, including apparent grammar and spelling errors, unless a correction was required to join OCR-split words.",
        "- Normalized connector capitalization only inside structured answer controls (for example DisplayPort).",
        "- Kept all official answers unchanged; conflicting official answers were not resolved by guessing.",
    ])
    if matching_notes:
        lines.extend(["", "## Match review notes", ""])
        lines.extend(f"- {note}" for note in matching_notes)
    return "\n".join(lines) + "\n"


def main() -> None:
    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    bank_entries = [entry for entry in raw if entry["sourceId"] == "bank-105"]
    pretest_entries = [entry for entry in raw if entry["sourceId"] == "pretest-70"]
    if len(bank_entries) != 105 or len(pretest_entries) != 70:
        raise ValueError("Raw source coverage must be 105 + 70")

    parsed = [parse_bank_entry(entry) for entry in bank_entries]
    questions, bank_by_page, bank_duplicate_count = merge_bank_duplicates(parsed)
    answer_conflicts, matching_notes = attach_pretest_sources(
        questions, bank_entries, bank_by_page, pretest_entries
    )

    errors: list[str] = []
    for question in questions:
        for error in validate_question(question):
            errors.append(f"{question['id']}: {error}")
    if errors:
        raise ValueError("\n".join(errors))

    payload = {
        "version": 1,
        "course": "ITS Device Configuration and Management",
        "sourceEntryCount": 175,
        "questions": questions,
    }
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    source_asset = ROOT / "extraction" / "source-pages" / "pretest-46.jpg"
    output_asset = (
        ROOT / "study-website" / "assets" / "source-pages" / "pretest-page-46.jpg"
    )
    output_asset.parent.mkdir(parents=True, exist_ok=True)
    if source_asset.exists():
        shutil.copyfile(source_asset, output_asset)
    elif not output_asset.exists():
        raise FileNotFoundError(
            "The pre-test page 46 evidence image is missing from both the extraction "
            "cache and the delivered source-page assets."
        )
    DATA_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    REPORT_PATH.write_text(
        create_report(
            questions,
            bank_duplicate_count,
            answer_conflicts,
            matching_notes,
        ),
        encoding="utf-8",
    )
    print(
        f"Validated {len(questions)} canonical questions "
        f"({sum(question['needsReview'] for question in questions)} need review)."
    )


if __name__ == "__main__":
    main()
