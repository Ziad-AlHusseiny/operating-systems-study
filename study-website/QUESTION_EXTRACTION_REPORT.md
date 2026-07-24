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

- Questions requiring manual review: 1
- `q-103` — Answer conflict: pre-test PDF page 46 highlights Differential, while the 105-question bank PDF page 38 marks Incremental. Sources: ITS OD 103 Pre-Test.pdf page 46

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

## Match review notes

- Answer conflict: pre-test PDF page 46 highlights Differential, while the 105-question bank PDF page 38 marks Incremental.
- Low OCR match confidence for pre-test question 42 (page 48) matched to bank page 41.
