.. _git-image-source-setup:

Git Image Source Setup
======================

{CB} reads any information about a KIWI image and its metadata
from a specified git repository. This includes the following
types of information:

The image configuration files:
  These are all files to build a KIWI image. For details
  see: https://osinside.github.io/kiwi/overview.html

The :file:`cloud_builder.yml` project file:
  This file contains information for {CB} to know how
  the image should be build. It also contains information about
  the runner group that is eligible to pick up the build request.

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
    └── images
        └── leap
            └── test-image-disk
                ├── cloud_builder.yml
                ├── appliance.kiwi
                └── config.sh

.. note::

   It's important that all projects are stored below a
   directory called ``projects``. This is the only convention
   {CB} expects to be respected. Below ``projects`` any custom
   structure to store projects and image sources is allowed

Understanding :file:`cloud_builder.yml`
---------------------------------------

In general :file:`cloud_builder.yml` contains information about
how the image target should be build. A typical file looks like the
following:

.. code:: yaml

   schema_version: 0.1
   name: test-image-disk

   images:
     -
       arch: x86_64
       runner_group: suse
       selection:
         name: standard
         profiles:
           - A
           - B
         build_arguments:
           - "--clear-cache"


`schema_version`:
  {CB} validates any information send through the message broker and
  read by services via a Cerberus validated schema. Every schema comes
  with a version such that changes to the schema in the future becomes
  possible.

`name`:
  Specifies the name of the image project. It's advisable to use
  the same name as used in the KIWI image desription. When {CB}
  builds the image, the output filenames are the result of the KIWI
  image build and not connected to the name used here.

`images`:
  Contains the target information for images to build from the
  KIWI image description. The settings here allows to build the
  image with custom options, e.g for different profiles, call
  options or architectures.

  * `arch`:

    An architecture name. The name must match one of the
    names known to Python's `platform.machine()` names.

  * `runner_group`:

    The runner group specifies a name that matches with the runner_group
    setup on the runner instance. A request to build the image will
    only be taken by runners of that group. That way an image for
    e.g a specific architecture can be connected to a runner which is
    of that architecture.

  * `selection`:

    The selection is a name for a collection of KIWI build parameters
    and provides a namespace to group this information.
    
    * `name`:

      Name of the selection

    * `profiles`:

      List of KIWI profile names to use for building the image

    * `build_arguments`:

      List of KIWI caller arguments to pass in addition to the
      ones set by default

.. note::

   With the explanation on the git contents based on the
   example `cloud-builder-packages` repo, the next step
   could be to create the project specific git repo and
   place the desired image and metadata source files.
   It would also be possible to continue with the example
   git repo and move to the real sources later.

Learn how to setup the message broker service
:ref:`kafka-broker-setup`
