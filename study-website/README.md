# ITS Device Configuration and Management Study Website

This is a static study website built with plain HTML, CSS, JavaScript, JSON, and browser LocalStorage.

## Content

- 175 official source entries from the two supplied PDFs
- 103 unique questions after merging 72 duplicate source entries
- Practice, mock exam, question bank, revision summary, mistakes, and bookmarks
- One source-conflict item clearly marked as unscored

No answer or explanation was invented. See `QUESTION_EXTRACTION_REPORT.md` for the extraction record.

## Start

From the project folder, run:

```powershell
python -m http.server 8000 --directory study-website
```

Then open <http://127.0.0.1:8000>.

On Windows, you can also double-click `START_WEBSITE.bat` in the parent folder.

## Data

Progress is saved only in the current browser. Use **Progress Data → Export** to create a backup and **Import** to restore it.
