.. cloud-builder documentation master file

{CB} Documentation
===========================

.. note::
   {CB} is a fresh and new project. Some parts are still in development
   and some parts are still missing.

.. toctree::
   :maxdepth: 1

   infrastructure_setup
   commands

.. sidebar:: Links

   * `GitHub Sources <https://github.com/OSInside/cloud-builder>`__
   * `RPM Packages <http://download.opensuse.org/repositories/Virtualization:/Appliances:/Staging>`__

Building Software Packages as a Service
---------------------------------------

The {CB} project provides a collection of services which allows
you to build software packages via a messaging API. Primarily
**rpm** packages but also other package formats like **deb**,
**pacman** and alike are possible.

If you don't want a monolithic server but small services for
dedicated tasks that can scale with the amount of tasks. If you
like to easily integrate a packaging service with other services.
If you like to build your product packages in an isolated
private network. If you like to build packages for an embedded
distribution. If you already have parts of your IT in the cloud.
If you like clean and test covered Python code. This project
might be interesting for you.

The  :ref:`services` are designed to run in cloud environments and
utilize message broker and VM instances cloud services to operate.
In general the environment to run the {CB} services is not restricted.
However, for the sake of this documentation and for my understanding
of a production ready pipeline the following cloud and services
will be used:

Amazon EC2:
  To let {CB} services run, instances in EC2 are used

Amazon MSK:
  {CB} services uses the Apacke Kafka message broker to communicate
  for request and response information. From a {CB} implementation
  perspective other brokers like RabbitMQ could be easily added via
  a new interface class. However, it depends on the broker features
  if it makes sense to use this message broker together with {CB}.
  Apacke Kafka was choosen because it allows for the
  *Publish/Subscribe* mode and for the *Shared Queue* mode in a
  nice way. Especially The *Shared Queue* mode in combination
  with the topic partition setup is used to distribute build requests
  across the available runner instances.

Git:
  The package sources must be stored in a git repository and the
  {CB} services fetches information from there as needed

Learn how to setup the infrastructure to start with {CB}
:ref:`infrastructure-setup`

Contact
-------

* `Matrix <https://matrix.org>`__

  An open network for secure, decentralized communication. Please find the
  ``#kiwi:matrix.org`` room via
  `Matrix <https://matrix.to/#kiwi:matrix.org>`__ on the web
  or by using the supported
  `clients <https://matrix.org/docs/projects/clients-matrix>`__.
