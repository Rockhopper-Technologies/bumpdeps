..
  Copyright 2022 - 2023 Avram Lubkin, All Rights Reserved

  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. start-badges

| |gh_actions| |pypi|

.. |gh_actions| image:: https://img.shields.io/github/actions/workflow/status/Rockhopper-Technologies/bumpdeps/tests.yml?event=push&logo=github-actions&style=plastic
    :target: https://github.com/Rockhopper-Technologies/bumpdeps/actions/workflows/tests.yml
    :alt: GitHub Actions Status

.. |pypi| image:: https://img.shields.io/pypi/v/bumpdeps.svg?style=plastic&logo=pypi
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/bumpdeps


.. end-badges

.. contents::
   :depth: 2

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


Using BumpDeps with GitHub Actions
==================================

Configure Deploy Key
--------------------

It is recommended to create a deploy key. This allows CI tests to run on the pull request created.
If you use the default permissions, the pull request will still be created, but it won't trigger
CI tests. There are alternative ways to accomplish this. Find more information on this here__.

__ https://github.com/peter-evans/create-pull-request/blob/main/docs/concepts-guidelines.md#triggering-further-workflow-runs


1. Create an SSH keypair, leave the passphrase blank.

   .. code:: console

    $ ssh-keygen -t ed25519 -f github_deploy

   This will create two files in the current directory

   - github_deploy
      The private key

   - github_deploy.pub
      The public key

2. Add the public key (contents of github_deploy.pub) as a deploy key under repo settings

   **IMPORTANT: check the box for "Allow write access"**

   Instructions for configuring deploy keys can be found here__.

   __ https://docs.github.com/en/developers/overview/managing-deploy-keys#deploy-keys

3. Create a repo secret named PRIVATE_KEY under repo settings with private key
   (contents of github_deploy) as the value

   Instructions for creating repository secrets can be found here__.

   __ https://docs.github.com/en/actions/security-guides/encrypted-secrets#creating-encrypted-secrets-for-a-repository


.. _peter-evens/create-pull-request: https://github.com/marketplace/actions/create-pull-request

Example GitHub Actions configuration
------------------------------------

This example avoids use of third-party actions, however it could be simplified
by utilizing `peter-evens/create-pull-request`_.

.. code:: yaml

  name: Update Dependencies

  on:
    schedule:
      # Every Monday at 1 AM
      - cron: '0 1 * * 1'

  jobs:
    Update_Deps:

      runs-on: ubuntu-latest
      name: ${{ matrix.name || matrix.args }}

      strategy:
        fail-fast: false
        matrix:
          args: [extras_1, extras_2]
          include:

          - args: '-b'
            name: Base Dependencies

          - args: '-a -i toml.*'
            name: All TOML libs

      env:
        DEPS_UPDATED: false

      steps:
        - uses: actions/checkout@v3
          with:
            ssh-key: ${{ secrets.PRIVATE_KEY }}

        - name: Install latest Python
          uses: actions/setup-python@v4
          with:
            python-version: 3.x

        - name: Install bumpdeps
          run: pip install bumpdeps

        - name: Update deps
          run: |
            set -x
            bumpdeps ${{ matrix.args }}
            git diff --quiet || echo "DEPS_UPDATED=true" >> $GITHUB_ENV

        - name: Create PR
          env:
            GH_TOKEN: ${{ github.token }}
          run: |
            set -x
            PR_BRANCH=bumpdeps/$(echo ${{ matrix.name || matrix.args }} | tr ' ' _)_${{ github.run_id }}
            PR_MSG="BumpDeps: ${{ matrix.name || matrix.args }}"

            # Configure Git
            git config --global user.name "BumpDeps"
            git config --global user.email "<>"

            # Create commit in new branch
            git checkout -b $PR_BRANCH
            git commit -a -m "$PR_MSG"
            git --no-pager log -n 2
            git push -u origin $PR_BRANCH

            # Create PR
            gh pr create -B main -H $PR_BRANCH --title "$PR_MSG" --body "Created by Github Action"
          if: env.DEPS_UPDATED == 'true'
