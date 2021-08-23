.. _auto_rebuild_on_build_dependencies:

Auto Rebuild on Package Build Dependency Changes
================================================

.. note::

   I need to implement the cb-depsolver service first

.. note:: Design Idea

   1. Use libsatsolver via the libsolv python binding as
      implemented in the KIWI API and command
      `kiwi image info --description cloud_builder.kiwi --resolve-package-list`
      Solving over the `cloud_builder.kiwi` file provides the dependency
      tree for all package build required packages (BuildRequires).

   2. Create a shasum over the dependency result from step 1

   3. Compare the shasum from the solver result with a former solver
      result and send a package build request to the message broker
      if there was a change

   4. Periodically run the solver operations over all packages.
      This is a CPU intensive task.

   The detection of a dependency change via the shasum is the simplest
   solution. Maybe there could be a more fine grained detection
   mechanism. The dependency result would contain all information
   to apply for other ways to detect a dependency change that should
   trigger a rebuild
