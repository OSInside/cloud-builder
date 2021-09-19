cb-info
=======

SYNOPSIS
--------

.. code:: bash

   cb-info -h | --help
   cb-info
       [--update-interval=<time_sec>]
       [--poll-timeout=<time_msec>]

DESCRIPTION
-----------

cb-info - lookup package/image information. The package/image
builds on a runner contains a number of files like
the following example:

.. code:: bash

   /var/tmp/CB/projects/PROJECT/
       ├── package@DIST.ARCH/
       ├── package@DIST.ARCH.build.log
       ├── package@DIST.ARCH.pid
       ├── package@DIST.ARCH.prepare.log
       ├── package@DIST.ARCH.result.yml
       ├── package@DIST.ARCH.run.log
       ├── package@DIST.ARCH.sh
       ├── package@DIST.ARCH.solver.json
       ├── ...
       ├── image@ARCH/
       ├── image@ARCH.build.log
       ├── image@ARCH.pid
       ├── image@ARCH.result.yml
       ├── image@ARCH.sh
       └── image@ARCH.solver.json

The local file information is used to construct
a response record with information about the
package/image build:

OPTIONS
-------

--update-interval=<time_sec>

  Optional update interval to reconnect to the
  message broker. Default is 10sec

--poll-timeout=<time_msec>

  Optional message broker poll timeout to return if no
  requests are available. Default: 5000msec

