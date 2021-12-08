.. cloud-builder documentation master file

{CB} Documentation
===========================

.. note::
   This documentation covers {CB} |version|- A package and
   appliance build backend primarily used as IaaS system.

.. toctree::
   :maxdepth: 1

   quickstart
   cluster_setup_from_scratch
   cluster_setup_from_cb_amis
   commands

.. sidebar:: Links

   * `GitHub Sources <https://github.com/OSInside/cloud-builder>`__
   * `RPM Packages <http://download.opensuse.org/repositories/Virtualization:/Appliances:/CloudBuilder>`__
   * `Amazon EC2 Images <https://download.opensuse.org/repositories/Virtualization:/Appliances:/CloudBuilder:/EC2:/fedora/images>`__

Building Software Packages and Appliances as a Service
------------------------------------------------------

The {CB} project provides a collection of services which
allows to stand up a package and appliance building backend to
build software packages as well as system images through a
messaging API. Primarily **rpm** and **deb** package formats
are supported as well as any image type supported by the
`KIWI <https://osinside.github.io/kiwi>`__ appliance builder.
{CB} is designed to run in cloud environments and this
documentation describes how to run {CB} in
`AWS (Amazon Web Services)`. However, in general the environment
to run the {CB} services is not restricted to a specific
cloud framework.

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

Architecture
------------

The {CB} architecture consists out of three major components:

The Sources:
  The package and image sources and all metadata to build them with {CB}
  must be stored in a git repository from which the {CB} services fetches
  information. The idea behind this is that package sources and metadata
  is treated like code and git is great in managing code. The history
  in Git allows to track any information about changes in the life
  time of a package or image. For details how to setup the source
  repo see: :ref:`sources`

The Messaging API:
  {CB} services uses the Apache Kafka message broker to communicate
  for request and response information. From a {CB} implementation
  perspective other brokers could be added via a new interface
  class. However, it depends on the broker features if it makes
  sense to use this message broker together with {CB}. Apache Kafka
  was choosen because it allows for the *Publish/Subscribe* mode
  and for the *Shared Queue* mode in a nice way. Especially The
  *Shared Queue* mode in combination with the topic partition setup
  is used to distribute build requests across the available runner
  instances. For details how to setup the messaging API see:
  :ref:`kafka-broker-setup`

The {CB} Services:
  The {CB} services introduced in :ref:`services` implements the actual
  functionality to allow building a package, or fetching information
  about a package, or building repos from packages, and so on. The
  services runs on one or more machines representing a certain
  functionality like a `runner` to build packages and images or a
  `collector` to create repositories from build results. The collection
  of all machines represents the {CB} cluster.

The following diagram shows how the {CB} services play together
and provides a visual overview about the system.

.. figure:: .images/cb-design.png
    :align: center
    :alt: Cloud Builder Architecture

    Cloud Builder Architecture

.. note::
   The minimal infrastructure to build packages with {CB} requires:

   * A git repo with the package sources.
     There is the `cloud-builder-packages <https://github.com/OSInside/cloud-builder-packages>`__
     example repo
   * A Kafka message broker. The focus will be on
     `Amzon MSK <https://docs.aws.amazon.com/msk/latest/developerguide/before-you-begin.html>`__
   * A runner instance with the cb-info and cb-scheduler services running.

   As the idea of {CB} is to come up with a scalable system that
   is configurable to the needs of the user, some of the services
   are optional on top of the minimal infrastructure.

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
