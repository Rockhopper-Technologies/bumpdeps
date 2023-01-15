# -*- coding: utf-8 -*-
# Copyright 2022 - 2023 Avram Lubkin, All Rights Reserved

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Nox configuration file for BumpDeps
See https://nox.thea.codes/en/stable/config.html
"""

import nox
import tomli

BASE_PYTHON = '3.10'

with open('pyproject.toml', 'rb') as toml_file:
    CONFIG = tomli.load(toml_file)

DEPENDENCIES = CONFIG['project']['dependencies']
NOX_DEPENDENCIES = ("nox", "tomli")

# Nox options
nox.needs_version = ">=2022.8.7"
nox.options.stop_on_first_error = False
nox.options.error_on_missing_interpreters = False


@nox.session(python=BASE_PYTHON, tags=['lint'])
def pylint(session: nox.Session) -> None:
    """Run Pylint"""
    session.install('pylint', 'pyenchant', *NOX_DEPENDENCIES, *DEPENDENCIES)
    session.run('pylint', 'bumpdeps', 'noxfile.py')


@nox.session(python=BASE_PYTHON, tags=['lint'])
def flake8(session: nox.Session) -> None:
    """Run Flake8"""
    session.install('flake8')
    session.run('flake8', '--max-line-length', '100', '--benchmark')
