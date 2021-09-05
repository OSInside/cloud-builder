cb-collect
==========

SYNOPSIS
--------

.. code:: bash

   cb-collect -h | --help
   cb-collect --project=<github_project> --ssh-pkey=<ssh_pkey_file>
       [--ssh-user=<user>]
       [--timeout=<time_sec>]

DESCRIPTION
-----------

cb-collect - fetches/updates a git repository and
collects build results of package sources as organized
in the git tree. Each project in the git tree will
be represented as a package repository.

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

--ssh-pkey=<ssh_pkey_file>

  Path to ssh private key file to access runner data

--ssh-user=<user>

  User name to access runners via ssh, defaults to: ec2-user

--timeout=<time_sec>

  Wait time_sec seconds of inactivity on the message
  broker before return. Default: 30sec
