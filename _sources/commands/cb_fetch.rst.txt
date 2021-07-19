cb-fetch
========

SYNOPSIS
--------

.. code:: bash

   cb-fetch -h | --help
   cb-fetch --project=<github_project>
       [--update-interval=<time_sec>]
       [--single-shot]

DESCRIPTION
-----------

cb-fetch - fetches a git repository and manages content
changes on a configurable schedule. In case of a change
a rebuild request is send to the message broker

The tree structure in the git repository has to respect
a predefined layout like in the following example:

.. code:: bash

   projects
   ├── ...
   ├── PROJECT_A
   │   └── SUB_PROJECT
   │       └── ...
   └── PROJECT_B
       └── PACKAGE
           ├── _Defaults.get_cloud_builder_metadata_file_name()_
           ├── _Defaults.get_cloud_builder_kiwi_file_name()_
           ├── PACKAGE.changes
           ├── PACKAGE.spec
           └── PACKAGE.tar.xz

OPTIONS
-------

--project=<github_project>

  git clone source URI to fetch project with
  packages managed to build in cloud builder

--update-interval=<time_sec>

  Optional update interval for the project
  Default is 30sec

--single-shot

  Optional single shot run. Only clone the repo
