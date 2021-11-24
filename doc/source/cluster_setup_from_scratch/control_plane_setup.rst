.. _control-plane-setup:

Create and Install the Control Plane
====================================

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

   The used AMI ID points to a Leap system.

   Replace the camel case parameter values with your own.

   .. code:: bash

      leap_15_3_ami=ami-0b4f49bedf96b14c9
      username=ec2-user

2. **SSH to the control plane**

   .. code:: bash

      ssh -i PathToPkeyMatchingMySSHKeyPairName \
          ${username}@InstanceIP

3. **Install {CB} on the control plane**

   .. code:: bash

      sudo zypper addrepo https://download.opensuse.org/repositories/Virtualization:/Appliances:/CloudBuilder/openSUSE_Leap_15.3 cloud-builder
      sudo zypper install python3-cloud_builder

4. **Install Kafka admin utilities**

   .. code:: bash

      sudo zypper install java-1_8_0-openjdk
      wget https://archive.apache.org/dist/kafka/2.2.1/kafka_2.12-2.2.1.tgz
      tar -xzf kafka_2.12-2.2.1.tgz

.. _control-plane-config:

Control Plane Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now that the control plane runs the following configurations are required:

1. **Fetch the Zookeeper Connect String**

   * Open the Amazon MSK console at https://console.aws.amazon.com/msk
   * Click on your cluster
   * Click on `view client information`

   In the pop up window under the headline `Apache ZooKeeper connection`
   Copy and preserve this information temporarily

2. **Login to the Control Plane**

   .. code:: bash

      ssh -i PathToPkeyMatchingMySSHKeyPairName \
          ${username}@InstanceIP

3. **Create {CB} Publish/Subscribe message topics**

   A message queue in Kafka is named a `topic`. The following
   topics are used by {CB} in Publish/Subscribe mode. This means
   each message is broadcast to all readers. This setting applies
   to the topics `cb-response`, `cb-info-request`, `cb-info-response`.
   Create these topics as follows:

   .. code:: bash

      cd kafka_2.12-2.2.1
      for topic in cb-response cb-info-request cb-info-response; do
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
   assign 10 partitions to the topic that handles the requests. For more
   details on how kafka balances consumers click `here <https://stackoverflow.com/questions/40326600/balancing-kafka-consumers/40327547>`__

   At this point a decision about the later size of the system needs to
   be made. It's possible to change the assigned number of partitions at
   a later point in time. For this example setup the following conditions
   are set:

   * 2 runner groups, `fedora` and `suse`.
   * 2 partitions for each runner group

   This will require to run 4 runner instances later, 2 for each
   runner group. Create the topics for these setup as follows:

   .. code:: bash

      cd kafka_2.12-2.2.1
      for topic in fedora suse; do
          bin/kafka-topics.sh \
              --create \
              --zookeeper ZookeeperConnectString \
              --replication-factor 2 \
              --partitions 2 \
              --topic ${topic};
      done

5. **Set appropriate retention time for topics**

   By default kafka topics have a retention time of 7 days which is
   quite long for some of the topics created before. As a good
   start the following retention times should be set:

   Runner Group Topics: *60min*
     The runner group topics are the ones receiving the build
     requests. Keeping build requests for an hour should be enough
     to survive a potential kafka rebalance.
     
   cb-info-response and cb-info-request: *2min*
     The cb-info-* topics are used to communicate with the build
     cluster. It is expected that requests sent will be answered
     more or less immeditately. Thus the retention time for these
     topics should be small.

   cb-response: *keep or increase*
     The cb-response topic receives all messages from all {CB}
     services. It is used to watch the cluster for basically
     everything. The default retention time of 7 days is a good
     start but could also increased.

   .. code:: bash

      cd kafka_2.12-2.2.1
      for topic in fedora suse; do
          bin/kafka-topics.sh \
              --alter \
              --zookeeper ZookeeperConnectString \
              --config retention.ms=3600000 \
              --topic ${topic};
      done
      for topic in cb-info-response cb-info-request; do
          bin/kafka-topics.sh \
              --alter \
              --zookeeper ZookeeperConnectString \
              --config retention.ms=120000 \
              --topic ${topic};
      done

6. **Configure** `cb-ctl`

   Last step is the configuration of {CB} to allow access to the
   Kafka service and the later runners.

   * Open the Amazon MSK console at https://console.aws.amazon.com/msk
   * Click on your cluster
   * Click on `view client information`

   In the pop up window under the headline `Bootstrap servers`
   Copy and preserve this information temporarily

   Create the file :file:`/etc/cloud_builder_broker.yml` as follows:

   .. code:: bash

      sudo vi /etc/cloud_builder_broker.yml

   Place the following content:

   .. code:: yaml

      broker:
        host: BootstrapServersString
      this_host: external_IP_or_Hostname_of_this_instance

   For collecting build results and log information {CB} services
   uses `SSH` with public/private key authorization. This requires
   the setup of an SSH keypair associated with a trusted user on the
   runner. In the setup procedure of the runner this user is
   created and called `cb-collect`. In the setup procedure of the
   control plane the used SSH keypair is created once as folows:

   .. code:: bash

      ssh-keygen -t rsa -f ~/.ssh/id_cb_collect

   Create the file :file:`~/.config/cb/cbctl.yml` as follows:

   .. code:: bash

      vi ~/.config/cb/cbctl.yml

   Place the following content:

   .. code:: yaml

      cluster:
        ssh_user: cb-collect
        ssh_pkey_file: HOME/.ssh/id_cb_collect
        runner_count: 2

   Replace *HOME* with the absolute path to the home directory
   of the user that is expected to call `cb-ctl`

   .. note:: runner count

      The configured number of runners (2) in this example is
      optional but recommended and tells cb-ctl to expect
      information from 2 runners. This setting avoids unneeded
      wait times as explained in step 5 of the runner setup
      from here :ref:`runner-setup`

Congrats, the control plane is now running, the kafka message broker
is up and configured and `cb-ctl` would be ready for a first package
build request. However, there are no runners which could work on such
a request. Learn how to setup the {CB} runner(s) next: :ref:`runner-setup`
