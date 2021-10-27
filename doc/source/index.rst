.. cloud-builder documentation master file

{CB} Documentation
===========================

.. note::
   {CB} in version |version| is a new project in its early days.
   Some parts are still in development and some parts are still
   missing. For details on the current state or the roadmap to
   v1.x.x just reach out.

.. toctree::
   :maxdepth: 1

   infrastructure_setup
   source_setup
   kafka_broker_setup
   runner_setup
   request_package_build
   auto_rebuild_on_source_change
   auto_rebuild_on_build_dependencies
   collect_and_build_project_repos
   commands
   playground

.. sidebar:: Links

   * `GitHub Sources <https://github.com/OSInside/cloud-builder>`__
   * `RPM Packages <http://download.opensuse.org/repositories/Virtualization:/Appliances:/Staging>`__

Building Software Packages as a Service
---------------------------------------

The {CB} project provides a collection of services which
allows to stand up a package building backend to build software
packages through a messaging API. Primarily **rpm** packages but also
other package formats like **deb**, **pacman** and alike are possible.

Why
---

If small services for dedicated tasks that can scale with the
amount of tasks and use cases is preferred over a monolithic server.
If easy integration of packaging services with other services is
a priority. If building in an isolated private network should be
possible by utilizing cloud services. If build power, network
bandwidth and storage capacity should be a scalable factor in
the cloud. If managing package sources and build metadata
should be done completely in git. If one ore more of this aspects
are a matching criteria, this project might be interesting.

Design Aspects
--------------

The {CB} services introduced in :ref:`services` are designed to run in
cloud environments and utilizes *message broker* and *VM instances* cloud
services to operate. In general the environment to run the {CB} services is
not restricted to a specific framework. However, for the sake of this
documentation and for my understanding of a production ready pipeline the
following cloud and services will be used:

Amazon EC2:
  To let {CB} services run, instances in EC2 are used

Amazon MSK:
  {CB} services uses the Apacke Kafka message broker to communicate
  for request and response information. From a {CB} implementation
  perspective other brokers could be easily added via a new interface
  class. However, it depends on the broker features
  if it makes sense to use this message broker together with {CB}.
  Apacke Kafka was choosen because it allows for the
  *Publish/Subscribe* mode and for the *Shared Queue* mode in a
  nice way. Especially The *Shared Queue* mode in combination
  with the topic partition setup is used to distribute build requests
  across the available runner instances.

Git:
  The package sources and all {CB} metadata must be stored in a git
  repository and the {CB} services fetches information from there
  as needed. The idea behind this is that package sources and metadata
  is treated like code and git is great in managing code. The history
  in Git allows to track any information about changes in the life
  time of a package.

Learn how to setup the infrastructure to start with {CB}
:ref:`infrastructure-setup`

Contact
-------

* `Matrix <https://matrix.org>`__

  An open network for secure, decentralized communication.
  As this project uses appliance building technology and is also one
  of my crazy ideas, you can find help in the
  ``#kiwi:matrix.org`` room via
  `Matrix <https://matrix.to/#kiwi:matrix.org>`__ on the web
  or by using the supported
  `clients <https://matrix.org/docs/projects/clients-matrix>`__.

  Remember to have fun :-)
