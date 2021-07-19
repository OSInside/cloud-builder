cb-scheduler
============

SYNOPSIS
--------

.. code:: bash

   cb-scheduler -h | --help
   cb-scheduler
       [--update-interval=<time_sec>]
       [--poll-timeout=<time_msec>]
       [--package-limit=<number>]

DESCRIPTION
-----------

cb-scheduler - listens on incoming package build requests
from the message broker on a regular schedule. Only if
the max package to build limit is not exceeded, request
messages from the broker are accepted. In case the request
matches the runner capabilities e.g architecture it gets
acknowledged and removed from the broker queue.

A package can be build for different distribution targets
and architectures. Each distribution target/arch needs to
be configured as a profile in the .kiwi metadata and added
as effective build target in the package configuration file:

* Defaults.get_cloud_builder_metadata_file_name()

An example package config to build the xclock package
for the Tumbleweed distribution for x86_64 and aarch64
would look like the following:

.. code:: yaml

   schema_version: 0.1
   name: xclock

   distributions:
     -
       dist: TW
       arch: x86_64
       runner_group: suse

     -
       dist: TW
       arch: aarch64
       runner_group: suse

The above instructs the scheduler to create two buildroot
environments, one for Tumbleweed(x86_64) and one for
Tumbleweed(aarch64) and build the xclock package in each
of these buildroots. To process this properly the scheduler
creates a script which calls cb-prepare followed by cb-run
with the corresponding parameters for each element of the
distributions list. Each dist.arch build process is triggered
by one build request. In the above example two requests
to build all targets in the distributions list would be
required.

The dist and arch settings of a distribution are combined
into profile names given to cb-prepare as parameter and used
in KIWI to create the buildroot environment. From the above
example this would lead to two profiles named:

* TW.x86_64
* TW.aarch64

The .kiwi metadata file has to provide instructions
such that the creation of a correct buildroot for these
profiles is possible.

OPTIONS
-------

--update-interval=<time_sec>

  Optional update interval to reconnect to the
  message broker. Default is 10sec

--poll-timeout=<time_msec>

  Optional message broker poll timeout to return if no
  requests are available. Default: 5000msec

--package-limit=<number>

  Max number of package builds this scheduler handles
  at the same time. Default: 10
