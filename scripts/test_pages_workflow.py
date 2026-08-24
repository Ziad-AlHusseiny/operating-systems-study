"""Regression checks for the Pages workflow's executable dependencies."""

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "pages.yml"
PINNED_PYPDF_COMMAND = 'python -m pip install --disable-pip-version-check "pypdf==6.9.2"'


class PagesWorkflowTests(unittest.TestCase):
    def test_installs_the_pinned_pdf_parser_before_extraction_and_python_checks(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn(PINNED_PYPDF_COMMAND, workflow)
        install_index = workflow.index(PINNED_PYPDF_COMMAND)
        self.assertLess(
            install_index,
            workflow.index("Check committed source extraction artifacts"),
        )
        self.assertLess(install_index, workflow.index("Run Python unit suite"))


if __name__ == "__main__":
    unittest.main()
