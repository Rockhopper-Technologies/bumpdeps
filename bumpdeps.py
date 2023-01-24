# -*- coding: utf-8 -*-
# Copyright 2022 - 2023 Avram Lubkin, All Rights Reserved

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
**Bump Dependencies**

Utility for bumping dependency versions specified in pyproject.toml files
Attempts to adhere to specifications outlined in PEP 440 and PEP 508

While this author does not generally think upper pinning is appropriate in many
cases, there are some where it may be unavoidable. This utility is intended to
help in those cases to avoid dependency stagnation.

https://peps.python.org/pep-0440/
https://peps.python.org/pep-0508/
"""

import argparse
from collections import abc
from datetime import date as Date
from json import JSONDecodeError
import logging
from pathlib import Path
import re
import sys

import requests
import tomlkit
from tomlkit.exceptions import TOMLKitError
from packaging.requirements import Requirement, InvalidRequirement
from packaging.specifiers import Specifier, SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import Version


__version__ = '0.2.0'
__all__ = 'BumpDeps', 'BumpDepsError', 'main'

DESCRIPTION = "Utility for bumping dependencies in pyproject.toml files"
EPILOG = '''\
Upper pinning of dependencies is generally not a good idea outside of deployment.
This utility is intended for cases where it can't be avoided.
'''

LOGGER = logging.getLogger('bumpdeps')
LOGGER.addHandler(logging.NullHandler())

COMMENT_RE = re.compile(r'[\s#]*bumpdeps:\s*(.+)\s*$')
IGNORE_UNTIL_RE = re.compile(r'ignore-until\s*=\s*(\d{4}-\d{2}-\d{2})\s*$')


class BumpDepsError(Exception):
    """General exception class for BumpDep errors"""


def _dump_requirement(req):
    """
    Converts a Requirement to a string
    This is only needed because the default __str__ methods don't include spaces

    This can be removed if this issue is resolved
    https://github.com/pypa/packaging/issues/654
    """

    # pylint: disable=protected-access
    return ' '.join(filter(bool, (
        req.name,
        f'[{",".join(req.extras)}]' if req.extras else None,
        ', '.join(sorted(f'{spec.operator} {spec.version}' for spec in req.specifier._specs)),
        f'@ {req.url}' if req.url else None,
        f'; {req.marker}' if req.marker else None,
    )))


class PyPI:
    """
    Class for accessing package index
    Defaults to PyPI, but works with other compatible indexes
    """

    def __init__(self, base_url='https://pypi.org') -> None:
        self.base_url = base_url

    def get_latest_package_version(self, package):
        """
        Query latest package version from package index
        """

        url = '/'.join((self.base_url, 'pypi', canonicalize_name(package), 'json'))

        LOGGER.debug('Querying latest version for %s from %s', package, url)
        response = requests.get(url, headers={'Accept': 'application/json'}, timeout=5)

        try:
            response.raise_for_status()  # Improve error handling later
        except requests.HTTPError as e:
            raise BumpDepsError(
                f'Unable to query package index for {package}: {e} {response.text}'
            ) from e

        try:
            return response.json()['info']['version']
        except JSONDecodeError as e:
            raise BumpDepsError(f'Invalid JSON returned from package index: {e}') from e
        except KeyError as e:
            raise BumpDepsError(
                f'Unexpected JSON structure returned from package index: {response.json()}'
            ) from e


class BumpDeps:
    """
    Main class for bumping dependencies

    Defaults to using PYPI and pyproject.toml, but customizable
    """

    def __init__(self, filename, pkg_index=None) -> None:

        self.filepath = Path(filename)
        self.pkg_index = PyPI(pkg_index) if pkg_index else PyPI()

    def bump(self, base=True, extras=False, include=None, exclude=None, dry_run=False):
        """
        Bump dependencies

        If base is True, base dependencies are updated
        If extras is True, all optional dependencies are updated
        If extras is an iterable, only those optional dependencies will be updated

        """

        updates = {'dependencies': [], 'optional-dependencies': {}}

        LOGGER.debug('Loading configuration from %s', self.filepath)
        try:
            with self.filepath.open('r', encoding='utf-8') as config_file:
                config = tomlkit.load(config_file)
        except (OSError, TOMLKitError) as e:
            raise BumpDepsError(f'Error loading {self.filepath}: {e}') from e

        if 'project' not in config:
            raise BumpDepsError(f'No project section in file {self.filepath}')

        # Update base dependencies
        if base is True and 'dependencies' in config['project']:
            LOGGER.debug('Updating base dependencies')
            updates['dependencies'] = self._update_deps(
                config['project']['dependencies'], include=include, exclude=exclude
            )

        # Update optional dependencies
        opt_deps = config['project'].get('optional-dependencies')

        if opt_deps and extras is True:
            for extra, section in config['project']['optional-dependencies'].items():
                LOGGER.debug('Updating optional dependencies for extra %s', extra)
                updates['optional-dependencies'][extra] = self._update_deps(
                    section, include=include, exclude=exclude)

        elif opt_deps and isinstance(extras, abc.Iterable):
            for extra in extras:
                if extra not in opt_deps:
                    LOGGER.error('Unknown section for optional dependencies: %s', extra)
                    continue

                LOGGER.debug('Updating optional dependencies for extra %s', extra)
                updates['optional-dependencies'][extra] = self._update_deps(
                    opt_deps[extra], include=include, exclude=exclude)

        # If dry run, return changes
        if dry_run:
            LOGGER.debug('Dry run. No changes persisted')
            return updates

        # Write toml to temp file
        if updates['dependencies'] or any(updates['optional-dependencies'].values()):

            temp_path = self.filepath.with_suffix('._bumpdeps')
            LOGGER.debug("Writing output to temp file '%s'", temp_path)
            with temp_path.open('w', encoding='utf-8') as temp_file:
                tomlkit.dump(config, temp_file)

            LOGGER.debug("Moving '%s' to '%s'", temp_path, self.filepath)
            temp_path.replace(self.filepath)
        else:
            LOGGER.debug('No changes to persisted')

        return updates

    def _ignore_for_comment(self, comment):

        match = COMMENT_RE.search(comment)

        if match is None:
            return False

        directives = match[1]
        if 'ignore-until' in directives:
            date_match = IGNORE_UNTIL_RE.search(directives)
            if date_match is None:
                LOGGER.error('Invalid format for ignore-until: %s', directives)
            else:
                try:
                    return Date.fromisoformat(date_match[1]) > Date.today()

                except ValueError:
                    LOGGER.error('Invalid date provided for ignore-until: %s', date_match[1])

        # Skip if ignore
        return 'ignore' in directives

    def _update_deps(self, section, include=None, exclude=None):
        """
        Update dependencies for an extra section or base
        """

        updates = []

        # A little bit of a hack in order to be able to read comments
        for idx, spec in enumerate(section._value):  # pylint: disable=protected-access
            if not spec.value:  # tomlkit._ArrayItemGroup
                continue

            # Parse requirement
            try:
                req = Requirement(spec.value)
            except InvalidRequirement as e:
                raise BumpDepsError(f"Invalid requirement '{spec.value}': {e}") from e

            if exclude and re.match(exclude, req.name):
                LOGGER.debug('Skipping package %s for exclude filter: %s', req.name, exclude)
                continue

            if include and not re.match(include, req.name):
                LOGGER.debug('Skipping package %s for include filter: %s', req.name, include)
                continue

            # Check comments
            if spec.comment and self._ignore_for_comment(str(spec.comment)):
                LOGGER.debug('Skipping package %s for comment: %s', req.name, spec.comment)
                continue

            # No need to update if no specifiers are defined
            if not req.specifier:
                LOGGER.debug('Skipping package %s since no specifiers defined', req.name)
                continue

            # Get latest version
            latest = self.pkg_index.get_latest_package_version(req.name)
            LOGGER.debug('Latest version for package %s is %s', req.name, latest)

            # No need to update if latest version isn't precluded
            if next(req.specifier.filter((latest,)), False):
                LOGGER.debug('Skipping package %s since latest version applies', req.name)
                continue

            # Capture requirement before updating
            old_req = _dump_requirement(req)
            LOGGER.debug("Updating specifiers for requirement '%s'", old_req)

            # Update specifiers
            req.specifier = self._update_specifiers(req.specifier, latest)
            new_req = _dump_requirement(req)

            # Update section
            LOGGER.debug("Re-adding updated requirement '%s'", new_req)
            section[idx] = new_req
            updates.append((old_req, new_req))

        return updates

    def _update_specifiers(self, specifier_set, latest):
        """
        Update a specifier set for a dependency
        """

        resultant_specifiers = []
        for specifier in specifier_set:
            # No maximum version specified, so keep as is
            if specifier.operator in ('!=', '>=', '>'):
                resultant_specifiers.append(specifier)

            # Specific or max version specified, replace with the latest
            elif specifier.operator in ('==', '===', '<', '<='):
                version = Version(specifier.version)
                new = Specifier(f'{specifier.operator}{latest}')
                resultant_specifiers.append(new)

            # Compatibility operator, try to match places
            elif specifier.operator == '~=':
                version = Version(specifier.version)
                latest_version = Version(latest)

            # If maximum version is specified, see how many places are specified
                version = Version(specifier.version)

                # Less than 3 places are occupied and latest has at least 3, use 2
                if len(version.release) < 3 <= len(latest_version.release):
                    new = Specifier(f'~={".".join(map(str, latest_version.release[:2]))}')
                else:
                    new = Specifier(f'~={latest}')

                resultant_specifiers.append(new)

            else:  # pragma: no cover
                raise BumpDepsError(
                    f"Unexpected operator '{specifier.operator}' in '{specifier}'"
                )

        return SpecifierSet(','.join(map(str, resultant_specifiers)))


def cli(args=None):
    """
    Parse CLI arguments
    """

    parser = argparse.ArgumentParser(description=DESCRIPTION, epilog=EPILOG)

    parser.add_argument('-a', '--all', action='store_true', default=False,
                        help='Update all base and extra dependencies')
    parser.add_argument('-b', '--base', action='store_true', default=False,
                        help='Update base dependencies, default when no extras are provided')
    parser.add_argument('-n', '--no-base', action='store_true', default=False,
                        help='Do not update base dependencies, for use with --all')
    parser.add_argument('-i', '--include', metavar='REGEX',
                        help='Only include dependency names matching regex')
    parser.add_argument('-e', '--exclude', metavar='REGEX',
                        help='Exclude dependency names matching regex')
    parser.add_argument('-f', '--file', metavar='FILE', type=Path, default=Path('pyproject.toml'),
                        help="Path to TOML file, default: 'pyproject.toml'")
    parser.add_argument('--dry-run', action='store_true', default=False,
                        help='No changes made, but report what would have changed')
    parser.add_argument('--pkg-index', metavar='URL', default=None,
                        help='Package index URL, Default: https://pypi.org')
    parser.add_argument('extras', nargs='*', metavar='EXTRAS',
                        help='Extra dependency sections to bump, bump base if none provided')
    parser.add_argument('-d', '--debug', action='store_true', default=False,
                        help='Enable debug logging')

    options = parser.parse_args(args)

    if not options.file.is_file():
        parser.error(f'File {options.file} does not exist')

    if options.include:
        try:
            re.compile(options.include)
        except re.error as e:
            parser.error(f"Invalid regex '{options.include}' provided for --include: {e}")

    if options.exclude:
        try:
            re.compile(options.exclude)
        except re.error as e:
            parser.error(f"Invalid regex '{options.exclude}' provided for --exclude: {e}")

    log_level = logging.DEBUG if options.debug else logging.INFO
    logging.basicConfig(level=log_level)

    return options


def main(args=None):
    """
    Main entry point for CLI
    """

    options = cli(args)
    bumper = BumpDeps(options.file, options.pkg_index)
    try:
        updates = bumper.bump(
            (options.base or options.all or not options.extras) and not options.no_base,
            options.extras or options.all,
            include=options.include, exclude=options.exclude, dry_run=options.dry_run
        )
    except BumpDepsError as e:
        LOGGER.error('%s', e)
        sys.exit(8)

    # Notify user of updates
    if updates['dependencies'] or any(updates['optional-dependencies'].values()):

        print('Base Dependencies:')
        for entry in updates['dependencies']:
            print(f'    <-- {entry[0]}')
            print(f'    --> {entry[1]}')

        print('Optional Dependencies:')
        for extra, reqs in updates['optional-dependencies'].items():
            if not reqs:
                continue
            print(f'  {extra}:')
            for entry in reqs:
                print(f'    <-- {entry[0]}')
                print(f'    --> {entry[1]}')
    else:
        print('No updates required')

    # Set return value if an error was logged
    if LOGGER._cache.get(logging.ERROR):  # pylint: disable=protected-access
        sys.exit(9)

    sys.exit(0)


if __name__ == '__main__':
    main()
