cb-prepare
==========

SYNOPSIS
--------

.. code:: bash

   cb-prepare -h | --help
   cb-prepare --root=<root_path> --package=<package_path> --profile=<dist> --request-id=<UUID>

DESCRIPTION
-----------

cb-prepare - creates a chroot tree suitable to build a
package inside of it, also known as buildroot. The KIWI
appliance builder is used to create the buildroot
according to a metadata definition file from:

* Defaults.get_cloud_builder_kiwi_file_name()

which needs to be present as part of the package sources.

The build utility from the open build service is called
from within a simple run.sh shell script that is written
inside of the buildroot after KIWI has successfully created
it. After this point, the buildroot is completely prepared
and can be used to run the actual package build.

OPTIONS
-------

--root=<root_path>

  Base path to create chroot(s) for later cb_run

--package=<package_path>

  Path to the package

--profile=<dist>

  Distribution profile name as set int the .kiwi
  package buildroot metadata file

--request-id=<UUID>

  UUID for this prepare process
