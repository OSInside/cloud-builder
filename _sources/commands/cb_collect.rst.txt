cb-collect
==========

SYNOPSIS
--------

.. code:: bash

   cb-collect -h | --help
   cb-collect --project=<github_project>
       [--branch=<name>]
       [--update-interval=<time_sec>]

DESCRIPTION
-----------

cb-collect - fetches/updates a git repository and
collects build results of packages and images as they
are synced here from the runners. Each project in the git
tree will be represented as a package repository.

The tree structure of the repository tree follows the
git project structure like in the following example:

.. code:: bash

   REPO_ROOT
    ├── ...
    ├── PROJECT_A
    │   └── SUB_PROJECT
    │       └── REPO_DATA_AND_REPO_METADATA
    └── PROJECT_B
        └── REPO_DATA_AND_REPO_METADATA

The REPO_ROOT could be served to the public via a
web server e.g apache such that the repos will be
consumable for the outside world and package
managers

OPTIONS
-------

--project=<github_project>

  git clone source URI to fetch project with
  packages managed to build in cloud builder

--branch=<name>

  git branch name

--update-interval=<time_sec>

  Update interval to ask for new packages/images
  Default: 30sec
