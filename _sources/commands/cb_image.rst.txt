cb-image
========

SYNOPSIS
--------

.. code:: bash

   cb-image -h | --help
   cb-image --description=<image_description_path> --target-dir=<target_path> --bundle-id=<ID> --request-id=<UUID>
       [(--repo-server=<name> --repo-path=<path> --repo-arch=<name> --ssh-user=<user> --ssh-pkey=<ssh_pkey_file>)]
       [--local]
       [--profile=<name>...]
       [-- <kiwi_custom_build_command_args>...]

DESCRIPTION
-----------

cb-image - builds an image using KIWI.
Inside of the image_description_path a KIWI image
description is expected. The process of building the
image is two fold:

* Build the image
* Bundle image result file(s) into an rpm package

The created image root tree will be deleted after
the image build. The reason for this is that building
an image should always start from a clean state to
guarantee the root tree integrity with respect to the
used package repositories

OPTIONS
-------

--description=<image_description_path>

  Path to KIWI image description

--target-dir=<target_path>

  Path to create image result package

--bundle-id=<ID>

  Identifier added to the build result file names

--profile=<name>

  List of optional profile names to use for building.
  This option can be specified multiple times

--request-id=<UUID>

  UUID for this prepare process

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

--local

  Operate locally:

  * do not send results to the message broker
  * do not create dependency graph
  * run operations in debug mode

-- <kiwi_custom_build_command_args>

  List of additional kiwi build command arguments
  See 'kiwi-ng system build --help' for details
