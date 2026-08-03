"""
tests/test_report_writer_openai.py — LLM report-writer prototype (ADR-0010)

report_writer_openai.py makes a real, billed LLM call, so most of it can't
be unit-tested offline -- that's expected and by design (see README.md).
This file exists specifically to cover the one part of it that CAN and
SHOULD be tested without any API key or network call: _repo_root(), whose
buggy version (TD-79, found live 2026-08-03) went unnoticed by every prior
offline test run precisely because nothing tested it in isolation.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from report_writer_openai import _repo_root  # noqa: E402


def test_repo_root_is_not_the_llm_report_writer_directory_itself():
    """The TD-79 bug, made permanently unable to silently recur: _repo_root()
    must never equal the directory report_writer_openai.py itself lives in.
    That was exactly the bug -- .env was being looked for one level too
    deep, inside llm_report_writer/ rather than its parent."""
    this_file = Path(__file__).resolve()
    llm_report_writer_dir = this_file.parent.parent  # tests/ -> llm_report_writer/
    assert _repo_root() != llm_report_writer_dir


def test_repo_root_is_the_parent_of_llm_report_writer():
    this_file = Path(__file__).resolve()
    llm_report_writer_dir = this_file.parent.parent  # tests/ -> llm_report_writer/
    expected = llm_report_writer_dir.parent
    assert _repo_root() == expected


def test_repo_root_is_a_real_existing_directory():
    # Whatever it resolves to, it should be a real directory on disk --
    # catches a typo'd .parent chain producing a nonsense path that just
    # happens to not equal llm_report_writer/ itself.
    assert _repo_root().is_dir()


if __name__ == "__main__":
    import inspect
    failures = 0
    tests = [(n, f) for n, f in list(globals().items()) if n.startswith("test_") and inspect.isfunction(f)]
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {name}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
