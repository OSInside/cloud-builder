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

Create and Install the Control Plane
------------------------------------

The Control Plane is a machine with access to the message
broker such that configurations of the broker as well as
calling the `cb-ctl` command can be performed.

In a production environment usually many users will use
`cb-ctl` outside of the control plane. As there are many
different access scenarious thinkable, this documentation
is based on the most simple access method which is based
on `ssh` to the control plane and calling `cb-ctl` from
there. Please note this is not the recommended way for a
production environment.

.. note::

   The following requires Kafka to run. The steps to setup the
   control plane are documented based on Kafka running on Amazon MSK
   and with the control plane to be an instance running on
   Amazon EC2, both in the same region. If these prerequisites do
   not match your environment, some of the following information
   will not apply.

1. **Start an instance to become the control plane**

   The used AMI ID points to a Leap 15.3 system. Currently {CB}
   is packaged for Leap and Fedora. Thus the control plane could
   also be based on Fedora. The following launches for Leap.

   Replace the camel case parameter values with your own.

   .. code:: bash

      $ aws ec2 run-instances \
          --image-id ami-0b4f49bedf96b14c9 \
          --count 1 \
          --instance-type t2.micro \
          --key-name MySSHKeyPairName \
          --security-group-ids sg-MyGroup \
          --subnet-id subnet-MySubNet

2. **SSH to the control plane**

   .. code:: bash

      $ ssh -i PathToPkeyMatchingMySSHKeyPairName \
            ec2-user@InstanceIP

3. **Install {CB} on the control plane**

   .. code:: bash

      $ sudo zypper addrepo https://download.opensuse.org/repositories/Virtualization:/Appliances:/Staging/openSUSE_Leap_15.3 cloud-builder
      $ sudo zypper install python3-cloud_builder

4. **Install Kafka admin utilities**

   .. code:: bash

      $ sudo zypper install java-1_8_0-openjdk
      $ wget https://archive.apache.org/dist/kafka/2.2.1/kafka_2.12-2.2.1.tgz
      $ tar -xzf kafka_2.12-2.2.1.tgz

Control Plane Setup
-------------------

Now that the control plane runs the following configurations are required:

1. **Fetch the Zookeeper Connect String**

   * Open the Amazon MSK console at https://console.aws.amazon.com/msk
   * Click on your cluster
   * Click on `view client information`

   In the pop up window under the headline `Apache ZooKeeper connection`
   Copy and preserve this information temporarily

2. **Login to the Control Plane**

   .. code:: bash

      $ ssh -i PathToPkeyMatchingMySSHKeyPairName \
            ec2-user@InstanceIP

3. **Create {CB} Publish/Subscribe message topics**

   A message queue in Kafka is named a `topic`. The following
   topics are used by {CB} in Publish/Subscribe mode. This means
   each message is broadcast to all readers. This setting applies
   to the topics `cb-response`, `cb-info-request`, `cb-info-response`.
   Create these topics as follows:

   .. code:: bash

      $ cd kafka_2.12-2.2.1
      $ for topic in cb-response cb-info-request cb-info-response; do
            bin/kafka-topics.sh \
                --create \
                --zookeeper ZookeeperConnectString \
                --replication-factor 2 \
                --partitions 1 \
                --topic ${topic};
        done

4. **Create {CB} Shared message topic**

   {CB} is designed to scale automatically on the number of runner
   instances. This means if there are e.g 10 runners in the runner_group
   e.g `fedora`, it is expected that package requests gets distributed
   to all runners. For this concept to work in Kafka it's important to
   assign 10 partitions to the topic that handles the requests. At this
   point a decision about the later size of the system needs to be made.
   It's possible to change the assigned number of partitions at a later
   point in time. For this example setup the following conditions are
   set:

   * 2 runner groups, `fedora` and `suse`.
   * 2 partitions for each runner group

   This will require to run 4 runner instances later, 2 for each
   runner group. Create the topics for these setup as follows:

   .. code:: bash

      $ cd kafka_2.12-2.2.1
      $ for topic in fedora suse; do
            bin/kafka-topics.sh \
                --create \
                --zookeeper ZookeeperConnectString \
                --replication-factor 2 \
                --partitions 2 \
                --topic ${topic};
        done

5. **Configure `cb-ctl`**

   Last step is the configuration of {CB} to allow access to the
   Kafka service.

   * Open the Amazon MSK console at https://console.aws.amazon.com/msk
   * Click on your cluster
   * Click on `view client information`

   In the pop up window under the headline `Bootstrap servers`
   Copy and preserve this information temporarily

   Create the :file:`/etc/cloud_builder_broker.yml` as follows:

   .. code:: bash

       sudo vi /etc/cloud_builder_broker.yml

   Place the following content:

   .. code:: yaml

      broker:
        host: BootstrapServersString

Congrats, the control plane is now running, the kafka message broker
is up and configured and `cb-ctl` would be ready for a first package
build request. However, there are no runners which could work on such
a request. Learn how to setup the {CB} runner(s) next: :ref:`runner-setup`
