cb-run
======

SYNOPSIS
--------

.. code:: bash

   cb-run -h | --help
   cb-run --root=<root_path> --request-id=<UUID>
       [(--repo-server=<name> --repo-path=<path> --repo-arch=<name> --ssh-user=<user> --ssh-pkey=<ssh_pkey_file>)]
       [--local]
       [--clean]

DESCRIPTION
-----------

cb-run - builds packages by calling the run.sh script
which must be present in the given root_path. cb-run
is usually called after cb-prepare which creates an
environment to satisfy the cb-run requirements

The called run.sh script is expected to run a program
that builds packages and stores them below the path
returned by Defaults.get_runner_result_paths()

At the end of cb-run an information record will be send
to preserve the result information for later use

OPTIONS
-------

--root=<root_path>

  Path to chroot to build the package. It's required
  that cb-prepare has created that chroot for cb-run
  to work

--request-id=<UUID>

  UUID for this build process

--repo-path=<path>

  Path to place build results on the repo server

--repo-arch=<name>

  Architecture name as used in the cloud_builder
  metadata file to describe the package target

--repo-server=<name>

  Name or IP of collector repo server

--ssh-pkey=<ssh_pkey_file>

  Path to ssh private key file to access repo server

--ssh-user=<user>

  User name to access repo server

--clean

  Delete chroot system after build and keep
  only results if there are any

--local

  Operate locally:
  * do not send results to the message broker
