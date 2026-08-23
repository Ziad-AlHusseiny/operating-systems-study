# Source Ingestion Specification

## Purpose

This specification converts configured material files into auditable source records. Ingestion never changes source meaning: a source is either accepted with traceable evidence or routed to review.

## Source Lifecycle

```text
inventoried -> extracted -> visually-checked -> normalized -> accepted
                                      `-> needs-review
```

Every configured file is inventoried before extraction. There is no silent skipping. A missing, unreadable, password-protected, corrupt, unsupported, or partially extracted source enters `needs-review` with its failure and known location. Do not infer an answer, answer key, correction, or missing content from surrounding material.

## Required Audit Output

`SOURCE_AUDIT_REPORT.md` is required for each ingestion run. It records source counts by format and status; PDF page counts and PPTX slide counts; unreadable locations; OCR corrections; duplicate groups; answer-key presence or absence; and all review items. Each entry identifies the `source-` ID, original filename, checksum, extraction tool/version, and completion time.

## Format Rules

| Format | Inventory and extraction | Visual rendering | Provenance and confidence | Failure behavior |
| --- | --- | --- | --- | --- |
| PDF | Record filename, checksum, pages, encryption, and embedded text. Extract page-by-page; OCR image-only pages. | Render every page, and inspect pages containing questions, tables, diagrams, OCR, or low-confidence text. | Cite `page` number, extraction method, and confidence per page/span. Preserve page image links where used. | An unreadable page, failed OCR, or ambiguous layout is a review item; retain extracted portions and do not fill gaps. |
| DOCX | Record sections, headings, tables, images, comments, and page count when available. Extract paragraphs and table cells in document order. | Render the document; inspect tables, equations, images, headers/footers, and question/answer layouts. | Cite a stable `section` locator plus paragraph/table context; record confidence and renderer version. | A damaged element or uncertain order is `needs-review`; do not guess a heading, table cell, or answer key. |
| PPTX | Record slides, notes, layouts, text boxes, tables, media, and hidden slides. Extract content slide-by-slide. | Render every slide and inspect diagrams, overlays, notes-dependent content, and answer layouts. | Cite `slide` number and element context; record extraction and visual confidence. | Unsupported media, missing fonts, unreadable slide text, or ambiguous overlay order becomes review work. |
| Text / Markdown | Record byte size, encoding, line endings, headings, links, and code fences. Decode UTF-8 first, retaining exact line numbers. | Render Markdown and inspect tables, images, math, and linked local assets. | Cite `section` and line range; record decoding and normalization confidence. | Unknown encoding, malformed Markdown that changes meaning, or missing local assets is reported and not silently repaired. |
| CSV / JSON | Record schema, row count, encoding, delimiter (CSV), and JSON root type. Parse structurally and preserve row/order/path locations. | Render tabular previews; inspect headers, wrapped values, nested JSON, and fields that look like question/answer keys. | Cite `row` for CSV or stable JSON path/`section`; record parser and schema confidence. | Parse errors, duplicate keys, broken rows, or schema drift enter review; do not manufacture values. |
| Images | Record dimensions, format, checksum, orientation, and embedded metadata. OCR only as a derived layer. | View every image at readable resolution; inspect diagrams, handwriting, answer marks, and cropped edges. | Cite `image` locator and region description; record OCR confidence and all human corrections. | Blurry, cropped, illegible, or uncertain content is `needs-review`; OCR output is never accepted as an inferred answer. |

## Normalization and Acceptance

Normalization creates canonical whitespace, Unicode, headings, and location locators without discarding raw extracted text or visual references. It must retain source IDs, original locations, extraction metadata, confidence, and corrections. Acceptance requires inventory, extractability, required visual checks, valid provenance, and no unresolved meaning-changing issue. Duplicate candidates are grouped in the audit report; they are not deleted automatically.

## Answer-Key Boundaries

The audit explicitly records whether an answer key is present, absent, partial, unreadable, or conflicting. Only an explicit source answer key may populate an official answer. When no reliable answer key exists, preserve the question with `needsReview: true`, an empty or unscored answer according to its contract, and a review note. Generated content may reason from approved material, but it must not be represented as an official answer.
