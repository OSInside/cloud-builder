.. _quickstart:

Quick Start
===========

.. note::

   This document provides information how to get started with {CB}
   and follows up with information about the structure of the package
   and image source files such that {CB} can consume them.

The {CB} services are designed to let users create a build backend for
packages and images. However, for a quick start this is a lot of
information and can lead to an overload with information from different
technology areas.

So let's start in small steps and with the idea to just let {CB}
build a package and see how that works. For building a package
on your local system it would be enough to install the `python3-cloud_builder`
package and checkout the example `cloud-builder-packages <https://github.com/OSInside/cloud-builder-packages>`__ git repository
for some example package and image sources. Because there is no information
about the host system on which these packages would be installed, I'd
like to also eliminate that source of trouble and simply start a local
virtual machine of a `runner` image which exists for {CB} to usually
serve as one `runner` system in a {CB} cluster.

.. note::

   The requirements for the host system to perform the following
   steps are set to:

   * Qemu KVM installed and available on the host
   * A connection to the Internet

The following steps needs to be done to start a {CB} runner locally
on your system:

.. code:: bash

   $ wget https://download.opensuse.org/repositories/Virtualization:/Appliances:/CloudBuilder:/EC2:/fedora/images/CB-RunnerFedora.x86_64.raw.xz

   $ xz -d CB-RunnerFedora.x86_64.raw.xz

   $ qemu-kvm \
       -m 4096 \
       -netdev user,id=user0 \
       -device virtio-net-pci,netdev=user0 \
       -serial stdio \
       -drive file=CB-RunnerFedora.x86_64.raw,if=virtio

.. note::

   Login to the system with user `root` pwd `linux`. This login
   option is only available with direct console access. If this
   image is used in cloud frameworks all local login options will
   be disabled through `cloud-init`

Once logged in to the `runner` system, perform the following steps
to build a package. As example the `xsnow` package for `Debian unstable`
is used:

.. code:: bash

   cd cloud_builder_sources/projects/Debian/xsnow

   cb-ctl --build-package-local --dist unstable --arch x86_64

Congrats ! you build your first package with {CB}. Feel free to try other
package builds from the example git repo checkout in :file:`cloud_builder_sources`.
After this, a good next step is to get familiar with the {CB} metadata
which exists below the :file:`.cb` directory in each package and image
source data. Learn more about the {CB} source setup in the following
chapters.

.. _sources:

Cloud Builder Source Setup
--------------------------

.. toctree::
   :maxdepth: 1

   quickstart/git_package_source_setup
   quickstart/git_image_source_setup
