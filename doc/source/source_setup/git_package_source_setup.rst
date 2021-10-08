.. _git-package-source-setup:

Git Package Source Setup
========================

{CB} reads any information about a package and its metadata
from a specified git repository. This includes the following
types of information:

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

The :file:`.cb/cloud_builder.yml` project file:
  This file contains information for {CB} to know for which
  distribution and architecture the package should be build.
  It also contains information about the runner group that
  is eligible to pick up the build request.

The :file:`.cb/cloud_builder.kiwi` metadata file:
  This file contains instructions how to build the buildroot
  environment within the package should be build. The buildroot
  is created using `KIWI <https://osinside.github.io/kiwi>`__

Before creating the git repository, let's clone the
example **cloud-builder-packages** git repo from here:

.. code:: bash

   $ git clone https://github.com/OSInside/cloud-builder-packages.git

Understanding the project structure
-----------------------------------

By convention the {CB} package sources need to follow a
certain files/directory structure which is provided in the
reference `git clone` from above. In general the project structure
is aligned to the following layout:

.. code:: bash

    projects
    ├── ...
    │
    ├── PROJECT_A
    │   └── SUB_PROJECT
    │       └── ...
    │
    └── MS
        └── python-kiwi_boxed_plugin
            ├── .cb
            │    ├── cloud_builder.kiwi
            │    └── cloud_builder.yml
            ├── python-kiwi_boxed_plugin.changes
            ├── python-kiwi_boxed_plugin.spec
            ├── python-kiwi_boxed_plugin.tar.gz
            └── python-kiwi_boxed_plugin-rpmlintrc

.. note::

   It's important that all projects are stored below a
   directory called ``projects``. This is the only convention
   {CB} expects to be respected. Below ``projects`` any custom
   structure to store projects and package sources is allowed

Understanding :file:`.cb/cloud_builder.yml`
-------------------------------------------

In general :file:`.cb/cloud_builder.yml` contains information about
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

`schema_version`:
  {CB} validates any information send through the message broker and
  read by services via a Cerberus validated schema. Every schema comes
  with a version such that changes to the schema in the future becomes
  possible.

`name`:
  Specifies the name of the package to connect the project file with
  the actual package. The name must match the name of the package
  source directory.

`distributions`:
  Contains the target distribution(s) for which the package should be
  build.

  * `dist`:

    A custom name to identify the distribution. It's good
    to choose a name which makes it easy to get an idea about the
    target.

  * `arch`:

    An architecture name. The name must match one of the
    names known to Python's `platform.machine()` names.

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

  These profile names plays an important role in the setup of the
  following :file:`.cb/cloud_builder.kiwi` file.


Understanding :file:`.cb/cloud_builder.kiwi`
--------------------------------------------

The :file:`.cb/cloud_builder.kiwi` describes how the package buildroot
system should be installed. When {CB} builds a package it does it
in two steps. First step is the creation of an execution environment
(cb-prepare service) also named **buildroot**. The second step is to
call the `build <https://software.opensuse.org/package/build>`__ tool
via **chroot** inside of the execution environment (cb-run service).

A typical KIWI file to create that execution environment looks
like the following:

.. code:: xml

   <?xml version="1.0" encoding="utf-8"?>

   <image schemaversion="7.4" name="python-kiwi_boxed_plugin">
       <description type="system">
           <author>Packager Name</author>
           <contact>packager@example.com</contact>
           <specification>python-kiwi_boxed_plugin build worker</specification>
       </description>

       <profiles>
           <profile name="TW.x86_64" description="For Tumbleweed (x86_64)"/>
           <profile name="Fedora34.x86_64" description="For Fedora34 (x86_64)"/>
       </profiles>

       <preferences>
           <version>0.2.14</version>
           <rpm-excludedocs>true</rpm-excludedocs>
           <type image="tbz"/>
       </preferences>

       <packages type="bootstrap">
           <package name="build"/>
           <package name="rpm-build"/>
           <package name="rpm-devel"/>
       </packages>

       <preferences profiles="TW.x86_64">
           <packagemanager>zypper</packagemanager>
       </preferences>

       <preferences profiles="Fedora34.x86_64">
           <packagemanager>dnf</packagemanager>
       </preferences>

       <repository profiles="TW.x86_64">
           <source path="http://download.opensuse.org/tumbleweed/repo/oss"/>
       </repository>

       <repository profiles="Fedora34.x86_64">
           <source path="http://mirrors.eze.sysarmy.com/fedora/linux/releases/34/Everything/x86_64/os/"/>
       </repository>

       <packages type="bootstrap" profiles="TW.x86_64">
           <package name="python3-devel"/>
           <package name="python3-setuptools"/>
           <package name="fdupes"/>
       </packages>

       <packages type="bootstrap" profiles="Fedora34.x86_64">
           <package name="python3-devel"/>
           <package name="python3-setuptools"/>
           <package name="fdupes"/>
           <package name="bash"/>
           <package name="util-linux"/>
           <package name="make"/>
       </packages>
   </image>

* `<description>`:

  Some information about the author

* `<profiles>`

  As mentioned in the explanation about :file:`.cb/cloud_builder.yml`
  the profile section connects the `dist` and `arch` value into
  a profile name here. When {CB} calls KIWI to create the
  buildroot it passes the combined name as profile name
  to KIWI. That way it's possible to distinguish different
  buildroots according to the `dist` and `arch` settings
  in :file:`.cb/cloud_builder.yml`.

* `<preferences>`

  This section contains settings relevant for the package
  manager and has to define a type and version because the KIWI schema
  wants it. The type information is not used in the scope
  of {CB}. Therefore the most simple type setup was used.
  For the version information the recommendation is to use
  the package version as it's also present in the package
  source files.

* `<packages type="bootstrap">`

  This section not connected to a specific profile applies always.
  In this example it includes all those packages which are needed
  in any buildroot. This is only possible if the package names
  are not different between the distribution targets. In this
  particular case the packages listed are the same for Fedora
  and SUSE.

* `<preferences profiles="TW.x86_64">`
* `<preferences profiles="Fedora34.x86_64">`

  This section contains profile specific package manager settings

* `<repository profiles="TW.x86_64">`
* `<repository profiles="Fedora34.x86_64"`

  This section contains profile specific repository settings from
  which packages are fetched to install the buildroot

* `<packages type="bootstrap" profiles="TW.x86_64">`
* `<packages type="bootstrap" profiles="Fedora34.x86_64">`

  This section contains the profile specific packages list to
  meet the build dependencies of the package.

.. note::

   With the explanation on the git contents based on the
   example `cloud-builder-packages` repo, the next step
   could be to create the project specific git repo and
   place the desired package and metadata source files.
   It would also be possible to continue with the example
   git repo and move to the real sources later.

Learn how to setup the message broker service
:ref:`kafka-broker-setup`
