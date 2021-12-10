.. _services:

Overview Cloud Builder Services
===============================

.. note::

   This document provides a list of the existing {CB} services
   for version |version|.

.. toctree::
   :maxdepth: 1

   commands/cb_fetch
   commands/cb_scheduler
   commands/cb_prepare
   commands/cb_run
   commands/cb_image
   commands/cb_info
   commands/cb_depsolver
   commands/cb_collect
   commands/cb_ctl

cb-fetch:
  Clones the referenced package source git repository.
  In addition it provides a package rebuild service on
  source changes

cb-scheduler:
  Listens to incomming package build requests and builds the
  package with help from **cb-prepare** and **cb-run**.
  Also supports building OS images with help from **cb-image**.
  If a package or an image should be build is configured via
  the :file:`.cb/cloud_builder.yml` package metadata. Multiple
  schedulers on as many compute instances increases
  the build performance.

cb-prepare:
  Prepares the buildroot environment within the package gets
  build. Creation of that buildroot is done with
  `KIWI <https://osinside.github.io/kiwi>`__ which supports
  all major distributions, such that packages for a wide
  range of distributions can be build.

cb-run:
  Builds the package inside of the buildroot environment.
  {CB} uses SUSE's `build <https://software.opensuse.org/package/build>`__
  tool to build packages. The tool supports a wide range of
  package formats.

cb-image:
  Builds OS images using `KIWI <https://osinside.github.io/kiwi>`__

cb-info:
  Looks up package information. This service should run on
  any instance with a cb-scheduler such that information
  about packages built on that instance can be retrieved.

cb-depsolver:
  Computes build dependencies for each package in the git
  repository using the satsolver library. In case a dependency
  has changed the package gets rebuild.

cb-collect:
  Creates repositories from packages. Each runner syncs its
  build results to the collector, aka repo-server. cb-collect
  creates/updates on a regular schedule the repo metadata for
  the available packages. cb-collect also manages the repo
  content in case the git sources changes.

cb-ctl:
  {CB} control utility to communicate with services, send
  requests, get information and more
