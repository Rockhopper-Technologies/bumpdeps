# -*- coding: utf-8 -*-
# Copyright 2023 Avram Lubkin, All Rights Reserved

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
**BumpDeps class Unit Tests**
"""

import responses

import bumpdeps
from tests import DIFF_BASE, DIFF_EXTRAS, EXAMPLE, MockedResponse, write_and_diff


class TestBumpDeps(MockedResponse):
    """
    Tests for updating dependencies
    """

    @responses.activate
    def test_base(self):
        """Update only base dependencies"""

        with write_and_diff(EXAMPLE) as result:
            bumper = bumpdeps.BumpDeps(result.file)
            updates = bumper.bump()

        self.assertEqual(
            updates['dependencies'],
            [('packaging == 1.0.0', 'packaging == 23.1'), ('requests <= 2.0', 'requests <= 2.28.2')]
        )
        self.assertEqual(updates['optional-dependencies'], {})
        self.assertEqual(result.diff, DIFF_BASE)

    @responses.activate
    def test_base_no_deps(self):
        """No dependencies listed"""

        with write_and_diff('[project]\n') as result:
            bumper = bumpdeps.BumpDeps(result.file)
            updates = bumper.bump()

        self.assertEqual(updates['dependencies'], [])
        self.assertEqual(updates['optional-dependencies'], {})
        self.assertEqual(result.diff, tuple())

    @responses.activate
    def test_dry_run(self):
        """Updates returns, but file is not updated"""

        with write_and_diff(EXAMPLE) as result:
            bumper = bumpdeps.BumpDeps(result.file)
            updates = bumper.bump(dry_run=True)

        self.assertEqual(
            updates['dependencies'],
            [('packaging == 1.0.0', 'packaging == 23.1'), ('requests <= 2.0', 'requests <= 2.28.2')]
        )

        self.assertEqual(result.diff, tuple())

    @responses.activate
    def test_extras(self):
        """Update all extras"""

        with write_and_diff(EXAMPLE) as result:
            bumper = bumpdeps.BumpDeps(result.file)
            updates = bumper.bump(base=False, extras=True)

        self.assertEqual(updates['dependencies'], [])
        self.assertEqual(
            updates['optional-dependencies'],
            {
                'opt1': [('prefixed ~= 0.3.2', 'prefixed ~= 0.6.0')],
                'opt2': [('sphinx ~= 5.3', 'sphinx ~= 6.1')],
                'opt3': [('blessed < 1.16, >= 1.0', 'blessed < 1.19.1, >= 1.0')],
                'opt4': [('six == 1.7.1', 'six == 1.16.0')],
                'opt5': [],
            }
        )
        self.assertEqual(result.diff, DIFF_EXTRAS)

    @responses.activate
    def test_extras_specific(self):
        """Update specific extra"""

        with write_and_diff(EXAMPLE) as result:
            bumper = bumpdeps.BumpDeps(result.file)
            updates = bumper.bump(base=False, extras=('opt2',))

        self.assertEqual(updates['dependencies'], [])
        self.assertEqual(
            updates['optional-dependencies'],
            {
                'opt2': [('sphinx ~= 5.3', 'sphinx ~= 6.1')],
            }
        )

        self.assertEqual(
            result.diff, (
                "-     'sphinx ~= 5.3',",
                '+     "sphinx ~= 6.1",',
            )
        )

    @responses.activate
    def test_regex_exclude(self):
        """Exclude dependencies with regex"""

        with write_and_diff(EXAMPLE) as result:
            bumper = bumpdeps.BumpDeps(result.file)
            updates = bumper.bump(exclude='req.*')

        self.assertEqual(
            updates['dependencies'],
            [('packaging == 1.0.0', 'packaging == 23.1')]
        )
        self.assertEqual(updates['optional-dependencies'], {})

        self.assertEqual(
            result.diff, (
                "-     'packaging == 1.0.0',",
                '+     "packaging == 23.1",',
            )
        )

    @responses.activate
    def test_regex_include(self):
        """Include dependencies with regex"""

        with write_and_diff(EXAMPLE) as result:
            bumper = bumpdeps.BumpDeps(result.file)
            updates = bumper.bump(include='pack.*')

        self.assertEqual(
            updates['dependencies'],
            [('packaging == 1.0.0', 'packaging == 23.1')]
        )
        self.assertEqual(updates['optional-dependencies'], {})

        self.assertEqual(
            result.diff, (
                "-     'packaging == 1.0.0',",
                '+     "packaging == 23.1",',
            )
        )


class TestBumpDepsErrors(MockedResponse):
    """
    Tests for errors raise in BumpDeps class
    """

    @responses.activate
    def test_extras_unknown(self):
        """Unknown extras provided"""

        with write_and_diff(EXAMPLE) as result:
            bumper = bumpdeps.BumpDeps(result.file)
            with self.assertLogs('bumpdeps', level='ERROR') as logs:
                updates = bumper.bump(base=False, extras=('unknown',))

        self.assertEqual(
            logs.output,
            ['ERROR:bumpdeps:Unknown section for optional dependencies: unknown'],
        )

        self.assertEqual(updates['dependencies'], [])
        self.assertEqual(updates['optional-dependencies'], {})
        self.assertEqual(result.diff, tuple())

    def test_file_not_found(self):
        """Bad file name raises error"""

        filename = 'NOT_A_REAL_FILE.toml'
        bumper = bumpdeps.BumpDeps(filename)
        with self.assertRaisesRegex(bumpdeps.BumpDepsError, f'Error loading {filename}'):
            bumper.bump()

    @responses.activate
    def test_ignore_until_format_invalid(self):
        """ignore-until format is not valid"""

        with write_and_diff(
            '[project]\ndependencies = [\n"six == 1.7.1",  # bumpdeps: ignore-until=tomorrow\n]\n'
        ) as result:
            bumper = bumpdeps.BumpDeps(result.file)
            with self.assertLogs('bumpdeps', level='ERROR') as logs:
                updates = bumper.bump()

        self.assertEqual(
            logs.output,
            ['ERROR:bumpdeps:Invalid format for ignore-until: ignore-until=tomorrow'],
        )

        self.assertEqual(updates['dependencies'], [])
        self.assertEqual(updates['optional-dependencies'], {})
        self.assertEqual(result.diff, tuple())

    @responses.activate
    def test_ignore_until_date_invalid(self):
        """Data is not a valid date"""

        with write_and_diff(
            '[project]\ndependencies = [\n"six == 1.7.1",  # bumpdeps: ignore-until=2022-02-30\n]\n'
        ) as result:
            bumper = bumpdeps.BumpDeps(result.file)
            with self.assertLogs('bumpdeps', level='ERROR') as logs:
                updates = bumper.bump()

        self.assertEqual(
            logs.output,
            ['ERROR:bumpdeps:Invalid date provided for ignore-until: 2022-02-30'],
        )

        self.assertEqual(updates['dependencies'], [])
        self.assertEqual(updates['optional-dependencies'], {})
        self.assertEqual(result.diff, tuple())

    def test_requirement_invalid(self):
        """Requirement does not have valid format"""
        with write_and_diff('[project]\ndependencies = [\n"requests !! 1.2.3" \n]\n') as result:
            bumper = bumpdeps.BumpDeps(result.file)
            with self.assertRaisesRegex(bumpdeps.BumpDepsError, 'Invalid requirement'):
                bumper.bump()

    @responses.activate
    def test_response_error(self):
        """Bad response from package index"""
        with write_and_diff(
            '[project]\ndependencies = [\n"no_such_package == 1.2.3" \n]\n'
        ) as result:
            bumper = bumpdeps.BumpDeps(result.file)
            with self.assertRaisesRegex(
                bumpdeps.BumpDepsError, 'Unable to query package index for no_such_package'
            ):
                bumper.bump()

    @responses.activate
    def test_response_json_invalid(self):
        """Response from package index is not valid JSON"""
        with write_and_diff(
            '[project]\ndependencies = [\n"invalid_json == 1.2.3" \n]\n'
        ) as result:
            bumper = bumpdeps.BumpDeps(result.file)
            with self.assertRaisesRegex(
                bumpdeps.BumpDepsError, 'Invalid JSON returned from package index'
            ):
                bumper.bump()

    @responses.activate
    def test_response_json_unexpected(self):
        """Response from package index does not have expected structure"""
        with write_and_diff(
            '[project]\ndependencies = [\n"unexpected_json == 1.2.3" \n]\n'
        ) as result:
            bumper = bumpdeps.BumpDeps(result.file)
            with self.assertRaisesRegex(
                bumpdeps.BumpDepsError,
                "Unexpected JSON structure returned from package index: {'version': '1.2.3'}"
            ):
                bumper.bump()

    def test_toml_invalid(self):
        """Invalid TOML in file"""
        with write_and_diff('{"json": true}') as result:
            bumper = bumpdeps.BumpDeps(result.file)
            with self.assertRaisesRegex(bumpdeps.BumpDepsError, f'Error loading {result.file}'):
                bumper.bump()

    def test_toml_project_missing(self):
        """TOML file does not have required 'project' section"""
        with write_and_diff('[foobar]\nfoo = "bar"\n') as result:
            bumper = bumpdeps.BumpDeps(result.file)
            with self.assertRaisesRegex(bumpdeps.BumpDepsError, 'No project section in file'):
                bumper.bump()
