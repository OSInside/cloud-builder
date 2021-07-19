.. _git-package-source-setup:

Git Package Source Setup
========================

{CB} reads any information about a package from a given
git repository. This includes the following types of
information:

The package configuration files:
  These are files like the software source tarball, the
  .spec file for rpm packages or any other sort of setup
  file needed to build a package for the desired package
  manager.

  .. note::
     This documentation will not cover the package setup
     for the various package managers and expects the data
     to build a package to be present and in understanding
     by the author.

The :file:`cloud_builder.yml` project file:
  This file contains information for {CB} to know for which
  distribution and architecture the package should be build.
  It also contains information about the runner group that
  is eligible to pick up the build request.

The :file:`cloud_builder.kiwi` metadata file:
  This file contains instructions how to build the buildroot
  environment within the package should be build. The buildroot
  is created using `KIWI <https://osinside.github.io/kiwi>`__

To setup the git repository I suggest to start with the
example **cloud-builder-packages** git repo from here:

.. code:: bash

   $ git clone https://github.com/OSInside/cloud-builder-packages.git

Understanding the project structure
-----------------------------------

By convention the {CB} package sources has to follow the structure
you see in the git checkout. This means in general:

.. code:: bash

    projects
    ├── ...
    │
    ├── PROJECT_A
    │   └── SUB_PROJECT
    │       └── ...
    │
    └── PROJECT_B
        └── PACKAGE
            ├── cloud_builder.kiwi
            ├── cloud_builder.yml
            └── PACKAGE.source_files...

.. note::

   In your own git you need to make sure that all projects
   are stored below a directory called ``projects``. This is
   the only convention {CB} expects to be respected. Below
   ``projects`` you can freely choose the structure to store
   package sources


Understanding :file:`cloud_builder.yml`
---------------------------------------

In general the :file:`cloud_builder.yml` contains information about
the target distribution for which the package should be build.
A typical file looks like the following:

.. code:: yaml

   schema_version: 0.1
   name: python-kiwi_boxed_plugin

   distributions:
     -
       dist: TW
       arch: x86_64
       runner_group: suse

     -
       dist: Fedora34
       arch: x86_64
       runner_group: fedora

schema_version:
  {CB} validates any information send through the message broker and
  read by services via a Cerberus validated schema. Every schema comes
  with a version such that changes to the schema in the future becomes
  possible.

name:
  Specifies the name of the package to connect the project file with
  the actual package. The name must match the name of the **PACKAGE**
  source directory

distributions:
  Contains the target distribution(s) for which the package should be
  build

  * `dist`: A custom name to identify the distribution. It's good
    to choose a name which makes it easy to get an idea about the
    target

  * `arch`: An architecture name. The name must match one of the
    names known to Python's `platform.machine()` names

  * `runner_group`:
    The runner group specifies a name that matches with the runner_group
    setup on the runner instance. A request to build the package will
    only be taken by runners of that group. That way a package for
    e.g Fedora can be connected to a runner which is based on Fedora.
    It's possible to overcome incompatibilities between distributions
    like the rpm database that way.

  The information for `dist` and `arch` will be combined into a profile
  name `dist.arch`. In the above example this results into two profile
  names:

  .. code:: bash

     TW.x86_64
     Fedora34.x86_64

  These profile names plays a central role in the setup of the
  following :file:`cloud_builder.kiwi` file


Understanding :file:`cloud_builder.kiwi`
----------------------------------------
