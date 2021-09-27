cb-ctl
======

SYNOPSIS
--------

.. code:: bash

   cb-ctl -h | --help
   cb-ctl --build-package-local --dist=<name>
       [--clean]
   cb-ctl --build-package=<package> --project-path=<path> --arch=<name> --dist=<name> --runner-group=<name>
       [--clean]
   cb-ctl --build-image-local --selection=<name>
   cb-ctl --build-image=<image> --project-path=<path> --arch=<name> --runner-group=<name> --selection=<name>
   cb-ctl --build-dependencies=<package│image> --project-path=<path> --arch=<name> (--dist=<name>|--selection=<name>)
       [--timeout=<time_sec>]
   cb-ctl --build-dependencies-local (--dist=<name>|--selection=<name>)
   cb-ctl --build-log=<package│image> --project-path=<path> --arch=<name> (--dist=<name>|--selection=<name>)
       [--timeout=<time_sec>]
   cb-ctl --build-info=<package│image> --project-path=<path> --arch=<name> (--dist=<name>|--selection=<name>)
       [--timeout=<time_sec>]
   cb-ctl --get-binaries=<package│image> --project-path=<path> --arch=<name> --target-dir=<dir> (--dist=<name>|--selection=<name>)
       [--timeout=<time_sec>]
   cb-ctl --watch
       [--filter-request-id=<uuid>]
       [--filter-service-name=<name>]
       [--timeout=<time_sec>]


DESCRIPTION
-----------

Control plane for accessing the Cloud Builder services.

OPTIONS
-------

--build-package=<package>

  Create a request to build the given package.
  The provided argument is appended to the
  project-path and forms the directory path
  to the package in the git repository

  .. code:: bash

     projects/
       └── <project-path>/
              └── <package>/...

  Please note, the root directory is by convention
  a fixed name set to 'projects'

--build-package-local

  Build package from local checkout. The package
  sources will be looked up from the current working
  directory

--build-image-local

  Build image from local checkout. The image sources
  will be looked up from the current working directory

--build-image=<image>

  Create a request to build the given image.
  The provided image argument is used in the same
  way as the package argument from --build-package

--project-path=<path>

  Project path that points to the package in the git.
  See the above structure example

--arch=<name>

  Target architecture name

--dist=<name>

  Target distribution name for package builds

--selection=<name>

  Image selection name for image builds

--runner-group=<name>

  Send build request to specified runner group

--build-dependencies=<package>

  Provide latest build root dependency information

--build-log=<package>

  Provide latest raw package build log

--build-info=<package>

  Provide latest build result and status information

--get-binaries=<package>

  Download latest binary packages

--target-dir=<dir>

  Name of target directory for get-binaries download

--watch

  Watch response messages of the cloud builder system

--filter-request-id=<uuid>

  Filter messages by given request UUID

--filter-service-name=<name>

  Filter messages by given service name. Allowed
  service names are:

  * cb-fetch
  * cb-info
  * cb-run
  * cb-prepare
  * cb-scheduler
  * cb-image

--timeout=<time_sec>

  Wait time_sec seconds of inactivity on the message
  broker before return. Default: 30sec

--clean

  Delete package buildroot if present on the runner
  before building the package
