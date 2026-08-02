# Question Extraction Report

## Source coverage

- Total PDF pages: 183 (106 + 77)
- Official question source entries: 175 (105 + 70)
- Canonical unique questions: 103
- Duplicate source entries merged: 72
- Duplicate questions found inside the 105-question bank: 3
- Confirmed cross-PDF answer conflicts: 1

## Question types

- matching: 20
- mcq: 48
- multi-select: 9
- ordering: 1
- source-review: 3
- true-false-group: 22

## Manual review

- Questions requiring manual review: 5
- `q-015` — Marked answer preserved: both cited pages show Local administrator for both blanks, but that account type does not identify the System Information field that determines domain-join capability. Review the source key before use. Sources: Device_Configuration_and_Management_Eng_Ali_Mohamed.pdf page 16, ITS OD 103 Pre-Test.pdf page 21
- `q-087` — Marked answer preserved: the source marks System restore, but System Restore does not roll Windows back to a previous feature version and may remove an app installed after the restore point. No option cleanly satisfies the full stem. Sources: Device_Configuration_and_Management_Eng_Ali_Mohamed.pdf page 91
- `q-093` — Marked answer preserved as True, True, False, but a Microsoft account is not an inherent requirement for Windows Hello facial recognition. The first marked statement requires review. Sources: Device_Configuration_and_Management_Eng_Ali_Mohamed.pdf page 97
- `q-094` — Marked answer preserved: the source marks Ease of Access and Apps even though the stem asks for one option and Apps is not where Narrator is configured. Review the source key before use. Sources: Device_Configuration_and_Management_Eng_Ali_Mohamed.pdf page 98
- `q-103` — Answer conflict: pre-test PDF page 46 highlights Differential, while the 105-question bank PDF page 38 marks Incremental. Sources: ITS OD 103 Pre-Test.pdf page 46

## Arabic study guidance

- `data/explanations-ar.json` contains 103 generated Arabic translations and study explanations, one for each canonical question.
- The generated guidance is clearly labeled in the site and remains separate from official PDF questions and answers.
- Search covers English prompts plus Arabic translations, explanation paragraphs, and revision notes; source, topic, and type filters can be combined.
- Guidance appears after Practice answers and inside Question Bank and Exam Result review disclosures, but never during an active Mock Exam.
- Review items remain available in Practice and Question Bank, are always excluded from Mock Exams, and stay unscored wherever they are shown.
- The guidance does not resolve `q-103`; it describes the conflict and directs learners to pre-test PDF page 46 and 105-question bank PDF page 38.

## Arabic guidance maintenance

- Editable entries are split across `content/explanations-ar/q001-026.json`, `content/explanations-ar/q027-052.json`, `content/explanations-ar/q053-078.json`, and `content/explanations-ar/q079-103.json`.
- Run `python scripts/build_explanations.py` from the project root to merge the parts, require exact canonical-ID coverage, validate Arabic fields, and regenerate `study-website/data/explanations-ar.json`.
- Correct guidance in the matching content-part entry without changing the canonical prompt, official answer, or source references.
- Never select an answer for an unresolved official-source conflict. Preserve `needsReview`, the source references, and the unscored behavior.
- When a visibly marked source key is conceptually contradictory, preserve the marked answer for traceability, set `needsReview`, document the uncertainty, and keep the item unscored.

## Extraction quality

- The 105-question PDF was extracted from selectable text.
- Green text/check marks were treated as official correct answers; red text/cross marks were treated as wrong answers.
- The 70-question pre-test contains screenshot-only content and was extracted with rendered-page OCR.
- Red official-answer rectangles were detected on every pre-test question page.
- OCR text was matched to the canonical bank; low-confidence matches remain traceable through their source references.
- No PDF pages failed to render.

## Formatting corrections

- Collapsed broken line wrapping and repeated whitespace.
- Preserved source wording, including apparent grammar and spelling errors, unless a correction was required to join OCR-split words.
- Normalized connector capitalization only inside structured answer controls (for example DisplayPort).
- Kept all official answers unchanged; conflicting official answers were not resolved by guessing.
- Preserved visibly marked but conceptually contradictory keys for traceability; these items are flagged for review and remain unscored.

## Match review notes

- Answer conflict: pre-test PDF page 46 highlights Differential, while the 105-question bank PDF page 38 marks Incremental.
- Low OCR match confidence for pre-test question 42 (page 48) matched to bank page 41.
