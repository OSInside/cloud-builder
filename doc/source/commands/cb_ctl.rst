cb-ctl
======

SYNOPSIS
--------

.. code:: bash

   cb-ctl -h | --help
   cb-ctl --build=<package> --project-path=<path> --arch=<name> --dist=<name> --runner-group=<name>
       [--clean]
   cb-ctl --build-dependencies=<package> --project-path=<path> --arch=<name> --dist=<name>
       [--timeout=<time_sec>]
   cb-ctl --build-log=<package> --project-path=<path> --arch=<name> --dist=<name>
       [--timeout=<time_sec>]
   cb-ctl --build-info=<package> --project-path=<path> --arch=<name> --dist=<name>
       [--timeout=<time_sec>]
   cb-ctl --get-binaries=<package> --project-path=<path> --arch=<name> --dist=<name> --target-dir=<dir>
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

--build=<package>

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

--project-path=<path>

  Project path that points to the package in the git.
  See the above structure example

--arch=<name>

  Target architecture name

--dist=<name>

  Target distribution name

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

--timeout=<time_sec>

  Wait time_sec seconds of inactivity on the message
  broker before return. Default: 30sec

--clean

  Delete package buildroot if present on the runner
  before building the package
