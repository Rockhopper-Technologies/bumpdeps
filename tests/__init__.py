# -*- coding: utf-8 -*-
# Copyright 2023 Avram Lubkin, All Rights Reserved

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
**Common code for BumpDeps Unit Tests**
"""

from contextlib import contextmanager
import difflib
from dataclasses import dataclass
import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile

import responses


EXAMPLE = """
[project]
dependencies = [
    'packaging == 1.0.0',
    'requests <= 2.0',
    'enlighten == 1.11.1',
    'prefixed',
]
[project.optional-dependencies]
opt1 = [
    'jinxed == 1.2.0',
    'prefixed ~= 0.3.2',  # Non-actionable comment
]
opt2 = [
    'sphinx ~= 5.3',
]
opt3 = [
    'blessed >= 1.0, < 1.16',
]
opt4 = [
    'pydantic == 1.2',  # bumpdeps: ignore
    'fastapi == 0.76.0',  # bumpdeps: ignore-until=2200-01-01
    'six == 1.7.1',  # bumpdeps: ignore-until=1984-01-01
]
opt5 = [
    'pylint == 2.15.10'
]

"""

# File diff for base dependencies
DIFF_BASE = (
    "-     'packaging == 1.0.0',",
    '+     "packaging == 23.1",',
    "-     'requests <= 2.0',",
    '+     "requests <= 2.28.2",',
)

# File diff for all extras
DIFF_EXTRAS = (
    "-     'prefixed ~= 0.3.2',  # Non-actionable comment",
    '+     "prefixed ~= 0.6.0",  # Non-actionable comment',
    "-     'sphinx ~= 5.3',",
    '+     "sphinx ~= 6.1",',
    "-     'blessed >= 1.0, < 1.16',",
    '+     "blessed < 1.19.1, >= 1.0",',
    "-     'six == 1.7.1',  # bumpdeps: ignore-until=1984-01-01",
    '+     "six == 1.16.0",  # bumpdeps: ignore-until=1984-01-01',
)


@ dataclass
class Result:
    """
    Simple container to return data from write_and_diff()
    """

    diff: tuple = tuple()
    file: str = None

    # Only for main()
    exit_code: int = 0
    logs: list = None
    stderr: str = ''
    stdout: str = ''


@contextmanager
def write_and_diff(text):
    """
    Write data to a temporary file and return a summary of the differences on close
    """

    test_file = None
    result = Result()

    try:
        test_file = NamedTemporaryFile(mode='w+', encoding='utf-8')
        test_file.write(text)
        test_file.flush()
        result.file = test_file.name
        yield result

    finally:

        new_text = Path(test_file.name).read_text(encoding='utf-8')
        diff = difflib.ndiff(text.splitlines(), new_text.splitlines())
        result.diff = tuple(line for line in diff if line[0] in '-+')
        test_file.close()


class MockedResponse(unittest.TestCase):
    """
    Test case class with mocked PyPI responses
    """

    def setUp(self) -> None:

        responses.get('https://pypi.org/pypi/requests/json',
                      json={'info': {'version': '2.28.2'}}, status=200)

        responses.get('https://pypi.org/pypi/packaging/json',
                      json={'info': {'version': '23.1'}}, status=200)

        responses.get('https://pypi.org/pypi/enlighten/json',
                      json={'info': {'version': '1.11.1'}}, status=200)

        responses.get('https://pypi.org/pypi/blessed/json',
                      json={'info': {'version': '1.19.1'}}, status=200)

        responses.get('https://pypi.org/pypi/prefixed/json',
                      json={'info': {'version': '0.6.0'}}, status=200)

        responses.get('https://pypi.org/pypi/sphinx/json',
                      json={'info': {'version': '6.1.2'}}, status=200)

        responses.get('https://pypi.org/pypi/jinxed/json',
                      json={'info': {'version': '1.2.0'}}, status=200)

        responses.get('https://pypi.org/pypi/six/json',
                      json={'info': {'version': '1.16.0'}}, status=200)

        responses.get('https://pypi.org/pypi/pylint/json',
                      json={'info': {'version': '2.15.10'}}, status=200)

        responses.get('https://pypi.org/pypi/no-such-package/json',
                      json={"message": "Not Found"}, status=404)

        responses.get('https://pypi.org/pypi/invalid-json/json',
                      body='Hello!', status=200)

        responses.get('https://pypi.org/pypi/unexpected-json/json',
                      json={'version': '1.2.3'}, status=200)
