# -*- coding: utf-8 -*-
# Copyright 2022 - 2023 Avram Lubkin, All Rights Reserved

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Nox configuration file for BumpDeps
See https://nox.thea.codes/en/stable/config.html
"""

from pathlib import Path

import nox
import tomli

BASE_PYTHON = '3.10'

with open('pyproject.toml', 'rb') as toml_file:
    CONFIG = tomli.load(toml_file)

DEPENDENCIES = CONFIG['project']['dependencies']
TEST_DEPENDENCIES = CONFIG['project']['optional-dependencies']['tests']
NOX_DEPENDENCIES = ("nox", "tomli")

# Nox options
nox.needs_version = ">=2022.8.7"
nox.options.stop_on_first_error = False
nox.options.error_on_missing_interpreters = False


@nox.session(python=BASE_PYTHON, tags=['lint'])
def pylint(session: nox.Session) -> None:
    """Run Pylint"""
    session.install('pylint', 'pyenchant', *NOX_DEPENDENCIES, *DEPENDENCIES, *TEST_DEPENDENCIES)
    session.run('pylint', 'bumpdeps', 'noxfile.py', 'tests')


@nox.session(python=BASE_PYTHON, tags=['lint'])
def flake8(session: nox.Session) -> None:
    """Run Flake8"""
    session.install('flake8')
    session.run('flake8', '--max-line-length', '100', '--benchmark')


@nox.session(python=BASE_PYTHON, tags=['lint'])
def readme(session: nox.Session) -> None:
    """Check readme"""

    Path('build').mkdir(exist_ok=True)
    session.install('rst2html', 'Pygments')
    session.run('rst2html.py', '-v', '--strict', 'README.rst', 'build/README.html', external=True)


@nox.session(python=['3.7', '3.8', '3.9', '3.10', '3.11'], tags=['test'])
def test(session: nox.Session) -> None:
    """Run unit tests"""
    session.install('.[tests]')
    session.run('python', '-m', 'unittest', 'discover', '-s', 'tests', *session.posargs)


@nox.session(python=BASE_PYTHON, tags=['test'])
def coverage(session: nox.Session) -> None:
    """Run unit tests"""
    session.install('.[tests]', 'coverage[toml]')
    session.run('coverage', 'erase')
    session.run('coverage', 'run', '-m', 'unittest', 'discover', '-s', 'tests', *session.posargs)
    session.run('coverage', 'report')
