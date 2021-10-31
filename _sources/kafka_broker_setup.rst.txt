.. _kafka-broker-setup:

Kafka Message Broker Setup
==========================

The heart of {CB} is the message broker. The messaging system
is the foundation of the {CB} API. All data send and read is
validated against a Cerberus based schema definition. The used
schema implements the API for the service. Only successfully
validated data will be handled.

.. note::

   There are some messaging services available. Currently
   {CB} implements support for the Kafka message broker only.
   Thus the following information is specific to Apache Kafka

For {CB} it is immaterial from where it can access the kafka
service. Because of this reason it can be a self manufactored
local solution, an offer by a managed service provider like
`Aiven <https://aiven.io/>`__ or a cloud service offering like
Amazon MSK. For good performance it is recommended to place
the kafka service near to the {CB} services with regards to
the network and region.

.. note::

   The current implementation of kafka in {CB} assumes the most
   simple access method to the kafka service. This requires kafka
   to run in the same network from which cb- tools and services
   are used. If {CB} gains some attraction this will be extended
   such that the config file to store the access credentials can
   also work with SSL and certificate based information.

As the focus of this documentation is to run {CB} in the Amazon
cloud, the promotion for kafka is set to Amazon MSK. A good start
to get kafka running in Amazon can be found here:

* https://docs.aws.amazon.com/msk/latest/developerguide/getting-started.html

Once a kafka message broker is running in some way shape or form
the next step in setting up the {CB} build cluster is the launch of
the `control plane`. Learn how to start and configure the `control plane`
next: :ref:`control-plane-setup`
