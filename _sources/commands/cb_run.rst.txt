cb-run
======

SYNOPSIS
--------

.. code:: bash

   cb-run -h | --help
   cb-run --root=<root_path> --request-id=<UUID>

DESCRIPTION
-----------

cb-run - builds packages by calling the run.sh script
which must be present in the given root_path. cb-run
is usually called after cb-prepare which creates an
environment to satisfy the cb-run requirements

The called run.sh script is expected to run a program
that builds packages and stores them below the path
returned by Defaults.get_runner_results_root()

If the `build <https://software.opensuse.org/package/build>`__
script is used this will be the following directory lookup:

.. code:: bash

   root_path
   └── home
       └── abuild

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
