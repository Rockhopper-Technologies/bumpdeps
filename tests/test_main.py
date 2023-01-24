# -*- coding: utf-8 -*-
# Copyright 2023 Avram Lubkin, All Rights Reserved

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
**BumpDeps CLI Unit Tests**
"""

from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import StringIO

import responses

import bumpdeps
from tests import DIFF_BASE, DIFF_EXTRAS, EXAMPLE, MockedResponse, write_and_diff


class MockedCLI(MockedResponse):
    """
    Provides additional methods to simplify writing CLI tests
    """

    @contextmanager
    def write_and_diff(self, text):
        """
        Write data to a temporary file
        Return a summary of the differences and system outputs on close
        """

        with write_and_diff(text) as result:
            with self.assertRaises(SystemExit) as sys_exit:
                with redirect_stderr(StringIO()) as err, redirect_stdout(StringIO()) as out:
                    with self.assertLogs('bumpdeps', level='ERROR') as logs:
                        yield result

        result.exit_code = sys_exit.exception.code
        result.logs = logs.output
        result.stderr = err.getvalue()
        result.stdout = out.getvalue()

    def check_result_error(self, result, regex):
        """
        Check result object for single logged exception
        """

        self.assertEqual(result.exit_code, 8)
        self.assertEqual(len(result.logs), 1)
        self.assertRegex(result.logs[0], regex)
        self.assertEqual(result.stderr, '')
        self.assertEqual(result.stdout, '')
        self.assertEqual(result.diff, ())

    def check_no_error(self, result):
        """
        Checks result object to make sure there are no errors
        """

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(len(result.logs), 0)
        self.assertEqual(result.stderr, '')


class TestMain(MockedCLI):
    """
    Tests for CLI entry point
    """

    @responses.activate
    def test_all(self):
        """Update all dependencies"""

        with self.write_and_diff(EXAMPLE) as result:
            bumpdeps.main(('-f', result.file, '--all'))

        self.check_no_error(result)
        self.assertEqual(
            result.stdout,
            (
                'Base Dependencies:\n'
                '    <-- packaging == 1.0.0\n'
                '    --> packaging == 23.1\n'
                '    <-- requests <= 2.0\n'
                '    --> requests <= 2.28.2\n'
                'Optional Dependencies:\n'
                '  opt1:\n'
                '    <-- prefixed ~= 0.3.2\n'
                '    --> prefixed ~= 0.6.0\n'
                '  opt2:\n'
                '    <-- sphinx ~= 5.3\n'
                '    --> sphinx ~= 6.1\n'
                '  opt3:\n'
                '    <-- blessed < 1.16, >= 1.0\n'
                '    --> blessed < 1.19.1, >= 1.0\n'
                '  opt4:\n'
                '    <-- six == 1.7.1\n'
                '    --> six == 1.16.0\n'
            )
        )
        self.assertEqual(result.diff, DIFF_BASE + DIFF_EXTRAS)

    @responses.activate
    def test_base_no_deps(self):
        """No dependencies listed"""

        with self.write_and_diff('[project]\n') as result:
            bumpdeps.main(('-f', result.file))

        self.check_no_error(result)
        self.assertEqual(result.stdout, 'No updates required\n')
        self.assertEqual(result.diff, ())

    @responses.activate
    def test_base_only(self):
        """Update only base dependencies"""

        with self.write_and_diff(EXAMPLE) as result:
            bumpdeps.main(('-f', result.file))

        self.check_no_error(result)
        self.assertEqual(
            result.stdout,
            (
                'Base Dependencies:\n'
                '    <-- packaging == 1.0.0\n'
                '    --> packaging == 23.1\n'
                '    <-- requests <= 2.0\n'
                '    --> requests <= 2.28.2\n'
                'Optional Dependencies:\n'
            )
        )
        self.assertEqual(result.diff, DIFF_BASE)

    @responses.activate
    def test_dry_run(self):
        """Updates returns, but file is not updated"""

        with self.write_and_diff(EXAMPLE) as result:
            bumpdeps.main(('-f', result.file, '--dry-run'))

        self.check_no_error(result)
        self.assertEqual(
            result.stdout,
            (
                'Base Dependencies:\n'
                '    <-- packaging == 1.0.0\n'
                '    --> packaging == 23.1\n'
                '    <-- requests <= 2.0\n'
                '    --> requests <= 2.28.2\n'
                'Optional Dependencies:\n'
            )
        )
        self.assertEqual(result.diff, ())

    @responses.activate
    def test_extras(self):
        """Update all extras"""

        with self.write_and_diff(EXAMPLE) as result:
            bumpdeps.main(('-f', result.file, '--all', '--no-base'))

        self.check_no_error(result)
        self.assertEqual(
            result.stdout,
            (
                'Base Dependencies:\n'
                'Optional Dependencies:\n'
                '  opt1:\n'
                '    <-- prefixed ~= 0.3.2\n'
                '    --> prefixed ~= 0.6.0\n'
                '  opt2:\n'
                '    <-- sphinx ~= 5.3\n'
                '    --> sphinx ~= 6.1\n'
                '  opt3:\n'
                '    <-- blessed < 1.16, >= 1.0\n'
                '    --> blessed < 1.19.1, >= 1.0\n'
                '  opt4:\n'
                '    <-- six == 1.7.1\n'
                '    --> six == 1.16.0\n'
            )
        )
        self.assertEqual(result.diff, DIFF_EXTRAS)

    @responses.activate
    def test_extras_specific(self):
        """Update specific extra"""

        with self.write_and_diff(EXAMPLE) as result:
            bumpdeps.main(('-f', result.file,  'opt2', 'opt5'))

        self.check_no_error(result)
        self.assertEqual(
            result.stdout,
            (
                'Base Dependencies:\n'
                'Optional Dependencies:\n'
                '  opt2:\n'
                '    <-- sphinx ~= 5.3\n'
                '    --> sphinx ~= 6.1\n'
            )
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

        with self.write_and_diff(EXAMPLE) as result:
            bumpdeps.main(('-f', result.file,  '-e', 'req.*'))

        self.check_no_error(result)
        self.assertEqual(
            result.stdout,
            (
                'Base Dependencies:\n'
                '    <-- packaging == 1.0.0\n'
                '    --> packaging == 23.1\n'
                'Optional Dependencies:\n'
            )
        )
        self.assertEqual(
            result.diff, (
                "-     'packaging == 1.0.0',",
                '+     "packaging == 23.1",',
            )
        )

    @responses.activate
    def test_regex_include(self):
        """Include dependencies with regex"""

        with self.write_and_diff(EXAMPLE) as result:
            bumpdeps.main(('-f', result.file,  '-i', 'pack.*'))

        self.check_no_error(result)
        self.assertEqual(
            result.stdout,
            (
                'Base Dependencies:\n'
                '    <-- packaging == 1.0.0\n'
                '    --> packaging == 23.1\n'
                'Optional Dependencies:\n'
            )
        )
        self.assertEqual(
            result.diff, (
                "-     'packaging == 1.0.0',",
                '+     "packaging == 23.1",',
            )
        )


class TestMainErrors(MockedCLI):
    """
    Tests for CLI Errors
    """

    @responses.activate
    def test_extras_unknown(self):
        """Unknown extras provided"""

        with self.write_and_diff(EXAMPLE) as result:
            bumpdeps.main(('-f',  result.file, 'unknown'))

        self.assertEqual(result.exit_code, 9)
        self.assertEqual(len(result.logs), 1)
        self.assertEqual(
            result.logs[0], 'ERROR:bumpdeps:Unknown section for optional dependencies: unknown'
        )
        self.assertEqual(result.stderr, '')
        self.assertEqual(result.stdout, 'No updates required\n')
        self.assertEqual(result.diff, ())

    def test_file_not_found(self):
        """Bad file name results in error"""

        with self.write_and_diff(EXAMPLE) as result:
            bumpdeps.main(('-f', 'NOT_A_REAL_FILE.toml'))

        self.assertEqual(result.exit_code, 2)
        self.assertEqual(len(result.logs), 0)
        self.assertRegex(result.stderr, 'File NOT_A_REAL_FILE.toml does not exist')
        self.assertEqual(result.stdout, '')
        self.assertEqual(result.diff, ())

    @responses.activate
    def test_ignore_until_format_invalid(self):
        """ignore-until format is not valid"""

        with self.write_and_diff(
            '[project]\ndependencies = [\n"six == 1.7.1",  # bumpdeps: ignore-until=tomorrow\n]\n'
        ) as result:
            bumpdeps.main(('-f',  result.file,))

        self.assertEqual(result.exit_code, 9)
        self.assertEqual(len(result.logs), 1)
        self.assertEqual(
            result.logs[0], 'ERROR:bumpdeps:Invalid format for ignore-until: ignore-until=tomorrow'
        )
        self.assertEqual(result.stderr, '')
        self.assertEqual(result.stdout, 'No updates required\n')
        self.assertEqual(result.diff, ())

    @responses.activate
    def test_ignore_until_date_invalid(self):
        """Data is not a valid date"""

        with self.write_and_diff(
            '[project]\ndependencies = [\n"six == 1.7.1",  # bumpdeps: ignore-until=2022-02-30\n]\n'
        ) as result:
            bumpdeps.main(('-f',  result.file))

        self.assertEqual(result.exit_code, 9)
        self.assertEqual(len(result.logs), 1)
        self.assertEqual(
            result.logs[0], 'ERROR:bumpdeps:Invalid date provided for ignore-until: 2022-02-30'
        )
        self.assertEqual(result.stderr, '')
        self.assertEqual(result.stdout, 'No updates required\n')
        self.assertEqual(result.diff, ())

    def test_regex_exclude_invalid(self):
        """Regex for exclude in invalid"""

        with self.write_and_diff(EXAMPLE) as result:
            bumpdeps.main(('-f', result.file, '-e', '('))

        self.assertEqual(result.exit_code, 2)
        self.assertEqual(len(result.logs), 0)
        self.assertRegex(result.stderr,  r"Invalid regex '\(' provided for --exclude")
        self.assertEqual(result.stdout, '')
        self.assertEqual(result.diff, ())

    def test_regex_include_invalid(self):
        """Regex for include in invalid"""

        with self.write_and_diff(EXAMPLE) as result:
            bumpdeps.main(('-f', result.file, '-i', '('))

        self.assertEqual(result.exit_code, 2)
        self.assertEqual(len(result.logs), 0)
        self.assertRegex(result.stderr,  r"Invalid regex '\(' provided for --include")
        self.assertEqual(result.stdout, '')
        self.assertEqual(result.diff, ())

    def test_requirement_invalid(self):
        """Requirement does not have valid format"""

        with self.write_and_diff(
            '[project]\ndependencies = [\n"requests !! 1.2.3" \n]\n'
        ) as result:
            bumpdeps.main(('-f', result.file))

        self.check_result_error(result, 'Invalid requirement')

    @responses.activate
    def test_response_error(self):
        """Bad response from package index"""

        with self.write_and_diff(
            '[project]\ndependencies = [\n"no_such_package == 1.2.3" \n]\n'
        ) as result:
            bumpdeps.main(('-f', result.file))

        self.check_result_error(result, 'Unable to query package index for no_such_package')

    @responses.activate
    def test_response_json_invalid(self):
        """Response from package index is not valid JSON"""

        with self.write_and_diff(
            '[project]\ndependencies = [\n"invalid_json == 1.2.3" \n]\n'
        ) as result:
            bumpdeps.main(('-f', result.file))

        self.check_result_error(result, 'Invalid JSON returned from package index')

    @responses.activate
    def test_response_json_unexpected(self):
        """Response from package index does not have expected structure"""

        with self.write_and_diff(
            '[project]\ndependencies = [\n"unexpected_json == 1.2.3" \n]\n'
        ) as result:
            bumpdeps.main(('-f', result.file))

        self.check_result_error(result, 'Unexpected JSON structure returned from package index')

    def test_toml_invalid(self):
        """Invalid TOML in file"""

        with self.write_and_diff('{"json": true}') as result:
            bumpdeps.main(('-f', result.file))

        self.check_result_error(result, f'Error loading {result.file}')

    def test_toml_project_missing(self):
        """TOML file does not have required 'project' section"""

        with self.write_and_diff('[foobar]\nfoo = "bar"\n') as result:
            bumpdeps.main(('-f', result.file))

        self.check_result_error(result, 'No project section in file')
