.. start-badges

| |gh_actions| |pypi|

.. |gh_actions| image:: https://img.shields.io/github/actions/workflow/status/Rockhopper-Technologies/bumpdeps/tests.yml?event=push&logo=github-actions&style=plastic
    :target: https://github.com/Rockhopper-Technologies/bumpdeps/actions/workflows/tests.yml
    :alt: GitHub Actions Status

.. |pypi| image:: https://img.shields.io/pypi/v/bumpdeps.svg?style=plastic&logo=pypi
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/bumpdeps


.. end-badges


Overview
========

BumpDeps is a utility for bumping dependency versions specified in `pyproject.toml`_ files.
It attempts to adhere to specifications outlined in `PEP 440`_ and `PEP 508`_.

BumpDeps can be used as part of a release process or CI workflow to ensure pinned
dependencies do not become outdated.


.. _pyproject.toml: https://pip.pypa.io/en/stable/reference/build-system/pyproject-toml/
.. _PEP 440: https://peps.python.org/pep-0440/
.. _PEP 508: https://peps.python.org/pep-0508/


Background
==========

Typically, dependency versions should not have upper-bound pinning because this is a deployment
activity. Pinning dependencies moves the implicit security contract from the user to the maintainer.
Instead, automated CI testing should run regularly against the latest versions of dependencies with
any issues resolved quickly. Upper-bound pinning, if required, should be temporary and tied to an
issue or task.

So why does this tool exist? There may be cases where pinning is still done. Whether this is for
valid reasons or not, the dependencies in these cases can quickly become outdated. This tool is
intended to simplify the process of updating those dependencies.


Usage
=====

For the most basic usage, run bumpdeps in the root of a project.
This will bump the base dependencies found in pyproject.toml.

.. code-block:: console

    $ bumpdeps

To bump optional dependencies, simplify provide the name of the extra.

.. code-block:: console

    $ bumpdeps some_extra some_cooler_extra

To bump all dependencies, use ``--all`` or ``-a``

.. code-block:: console

    $ bumpdeps --all


For more granular options, see below.


Customizing
===========

BumpDeps behavior can be customized though the use of in-line comments.

If ``# bumpdeps: ignore`` is found after a dependency,
BumpDeps will skip updates for that dependency.

If ``# bumpdeps: ignore-until=YYYY-MM-DD`` is found after a dependency,
BumpDeps will skip updates for that dependency until the date provided.


CLI Arguments
=============

usage: bumpdeps [-h] [-a] [-b] [-i REGEX] [-e REGEX] [-f FILE] [--dry-run] [--pkg-index URL] [-d] [EXTRAS ...]

| **-a**
| **--all**

    Update dependencies for base and all extras

| **-b**
| **--base**

    Update base dependencies.

    This is the default when no extras are provided.
    Typically used in combination with specific extras.

| **-n**
| **--no-base**

    Do not update base dependencies.

    This is intended for use with `--all` when one want to update all optional
    dependencies without updating the base dependencies.

| **-i REGEX**
| **--include REGEX**

    Regular expression filter. Only dependencies matching the filter will be updated.

| **-e REGEX**
| **--exclude REGEX**

    Regular expression filter. Dependencies matching the filter will be skipped.

| **-f FILE**
| **--file FILE**

    Path to TOML file. Defaults to pyproject.toml in the current directory.

    This file is expected to compatible with the pyproject.toml format.

| **--dry-run**

    Show what changes would be made without making any changes.

| **--pkg-index DIR**

    URL of package index. Defaults to https://pypi.org.

    If using a custom URL, it must have an API compatible with PyPI.

| **-d**
| **--debug**

    Show debug output

| **-h**
| **--help**

    Show help message and exit
