.. _auto_rebuild_on_source_change:

Auto Rebuild on Package Source Change
=====================================

If packages should be rebuild on a change of the package
sources in the Git master branch, one option to do this is
to run the `cb-fetch` service. This service periodically
checks for changes in the git and creates package build
requests under the following conditions:

1. **Package source(s) has changed:**

  One ore more files of the package sources has changed.
  The created packaged build request is eligble to reuse
  an eventual existing buildroot on the selected runner

2. **Package source(s) and/or metadata has changed:**

  Similar to the first case with the difference that a
  change on the package metadata `.cb/cloud_builder.yml` and/or
  `.cb/build_root.kiwi` will force a cleanup and rebuild of
  an eventual existing buildroot on the selected runner

To start the `cb-fetch` service either a new instance in
the cloud must be started or the control plane instance
can be used. Since the control plane has no hard job to
perform it's fairly fine to use it as source control service
as well.

The following steps needs to be done run `cb-fetch` on the
control plane:

1. **Login to the control plane**

   See :ref:`control-plane-setup` for details

2. **Configure the fetcher update intervall**

   .. code:: bash

      $ sudo vi /etc/cloud_builder

      CB_UPDATE=30

   Change or keep the default value of 30 seconds as you see fit.

3. **Start** `cb-fetch` **service**

   .. code:: bash

      $ sudo systemctl start cb-fetch

To read the actions taken by the `cb-fetch` service one can watch
on the {CB} info response messages as follows:

.. code:: bash

   $ cb-ctl cb-ctl --watch \
       --filter-service-name cb-fetch \
       --timeout 200

In case cb-fetch created a new package build request, information
like in the following example will be provided:

.. code:: bash

   {
       "identity": "CBFetch:18.193.45.127:15259:xclock",
       "message": "Package update request scheduled",
       "project": "projects/MS/xclock",
       "request_id": "d309d5d2-f2e0-11eb-9538-06be1098538e",
       "response_code": "package rebuild due to source change",
       "schema_version": 0.2,
       "target": {
           "arch": "x86_64",
           "dist": "TW"
       }
   }

The provided `request_id` can be used to check on the status
of the package build process as follows:

.. code:: bash

   $ cb-ctl cb-ctl --watch \
       --filter-request-id d309d5d2-f2e0-11eb-9538-06be1098538e \
       --timeout 5
