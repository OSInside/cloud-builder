.. _request_package_build:

Request a Package Build
=======================

At this point the {CB} backend is running and uses
`https://github.com/OSInside/cloud-builder-packages`
as the package source Git repository.

As a first example let's build the `xclock` package from
the `MS` project as follows:

1. **Login to the control plane**

   See :ref:`control-plane-setup` for details

2. **Create a package build request via** `cb-ctl`

   .. code:: bash

      cb-ctl --build-package xclock --project MS \
          --arch x86_64 --dist TW --runner-group suse

   This will return with an information like the following:

   .. code:: bash

      [ INFO    ]: 09:31:15 | Message successfully sent to: suse
      {
          "action": "package rebuild requested",
          "package": {
              "arch": "x86_64",
              "dist": "TW"
          },
          "project": "projects/MS/xclock",
          "request_id": "e0adf9c6-1224-11ec-bdbe-06be1098538e",
          "runner_group": "suse",
          "schema_version": 0.2
      }

   .. note::

      Any request to {CB} services are identified through a reques_id
      in UUID format. It is recommended to filter output by that id.
      Otherwise all information available according to the configured
      retention time of the desired topic in Kafka will be returned.

3. **Watch how the request runs through the {CB} services**

   Each {CB} service logs information into the global response
   queue. For reading the contents of this queue the `--watch`
   option is used as follows:

   .. code:: bash

      cb-ctl --watch \
          --filter-request-id b88becf6-f04f-11eb-8cff-06be1098538e \
          --timeout 5

   .. note::

      Please be aware that any conversation with the {CB} services
      are based on sending a message to the message broker followed
      by a subsequent lookup of information from the message broker.
      This polling of information always ends after a configurable
      timeout of inactivity. By default the timeout value is set to
      a safe long delay. Usually you set the timeout to a much smaller
      value to avoid boring wait periods.

   A typical output from the above command could look like this

   .. code:: bash

      {
          "identity": "CBScheduler:18.193.45.127:20028:xclock",
          "message": "Accept package build request",
          "project": "projects/MS/xclock",
          "request_id": "e0adf9c6-1224-11ec-bdbe-06be1098538e",
          "response_code": "package request accepted",
          "schema_version": 0.2,
          "target": {
              "arch": "x86_64",
              "dist": "TW"
          }
      }
      {
          "identity": "CBPrepare:18.193.45.127:25128:xclock",
          "message": "Buildroot ready for package build",
          "package_prepare": {
              "build_root": "/var/tmp/CB/projects/MS/xclock@TW.x86_64",
              "exit_code": 0,
              "prepare_log_file": "/var/tmp/CB/projects/MS/xclock@TW.x86_64.prepare.log",
              "solver_file": "/var/tmp/CB/projects/MS/xclock@TW.x86_64.solver.json"
          },
          "project": "projects/MS/xclock",
          "request_id": "e0adf9c6-1224-11ec-bdbe-06be1098538e",
          "response_code": "build root setup succeeded",
          "schema_version": 0.2
      }
      {
          "identity": "CBRun:18.193.45.127:25226:projects/MS/xclock",
          "message": "Package build finished",
          "package": {
              "binary_packages": [
                  "/var/tmp/CB/projects/MS/xclock@TW.x86_64/home/abuild/rpmbuild/RPMS/x86_64/xclock-1.0.9-0.x86_64.rpm",
                  "/var/tmp/CB/projects/MS/xclock@TW.x86_64/home/abuild/rpmbuild/SRPMS/xclock-1.0.9-0.src.rpm"
              ],
              "exit_code": 0,
              "log_file": "/var/tmp/CB/projects/MS/xclock@TW.x86_64.build.log",
              "prepare_log_file": "/var/tmp/CB/projects/MS/xclock@TW.x86_64.prepare.log",
              "solver_file": "/var/tmp/CB/projects/MS/xclock@TW.x86_64.solver.json"
          },
          "project": "projects/MS/xclock",
          "request_id": "e0adf9c6-1224-11ec-bdbe-06be1098538e",
          "response_code": "package build succeeded",
          "schema_version": 0.2
      }

   As you can see from this information there are the three {CB}
   services `cb-scheduler`, `cb-prepare` and `cb-run` that worked
   on your package and built it.

4. **Fetch package binaries**

   For fetching the built binaries `cb-ctl` needs to be called
   as follows:

   .. code:: bash

      cb-ctl --get-binaries xclock --project-path MS \
          --arch x86_64 --dist TW --timeout 5 \
          --target-dir my-xclock

   .. note::

      The above call actually created a request to the info request
      queue which will be read by any runner. It can happen that
      different runners has built the same package. The current
      implementation fetches the latest built binaries available
      in the backend.

      This behavior is intentional and applies to all `cb-ctl` commands
      which fetches information from the system that are not connected
      to a specific `request_id`

Congrats, you should have picked out the first useful data from
{CB}. Learn how to automate certain parts of the system like it is
explained in :ref:`auto_rebuild_on_source_change` or
:ref:`auto_rebuild_on_build_dependencies`
