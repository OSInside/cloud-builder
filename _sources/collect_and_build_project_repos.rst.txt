.. _collect_and_build_project_repos:

Collect and Build Project Repos
===============================

.. note::

   I need to implement the cb-collector service first

.. note:: Design Idea

   1. Send info request for each package in a project for all
      dists and archs as configured in `cloud_builder.yml`

   2. Fetch the package(s) and build up the same tree as the
      package is organized in the git

   3. After fetching all packages from a project create
      a repo from it using e.g `createrepo` for rpm packages

   Periodically run this for each project in a threading
   daemon concept

   * Setup an apache server to serve the repo structure
   * Attach a volume to the instance to store the repos
