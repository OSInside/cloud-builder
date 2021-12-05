.. _cluster_setup_from_cb_amis:
  
Setup Cloud Builder From AMIs
=============================

.. warning::

   This document provides information how to setup {CB} from
   the AMI (Amazon Machine Images) registered in Amazon EC2.
   As of now the AMIs are not part of the general catalog and
   needs to be shared by me with interested people. Therefore
   the following procedure can only work if you reach out to
   me such that I can share the required AMI IDs with your
   Amazon account.

For a simple and straight forward way to setup {CB} in Amazon,
three pre-configured AMIs were registered. One to create an
instance for the `control-plane`, one for creating a `collector`
instance and one for creating [N with N>=1] `runner` instances. All
AMIs are based on the `Fedora` distribution and comes with many
tools from other distributions pre-installed, such that the runners
can build packages and images for a variety of different
distributions.

Prerequisites
-------------

.. warning::

   Prior launching AWS services, it's important to understand that
   infrastructure as a service produces costs. The following procedure
   is done in a low cost model but is **not** free of charge.
   Take this into account when working with the cloud.

The setup procedure will use the Amazon MSK (Kafka) service as
well as the Amazon EC2 (Compute Nodes) service. For launching,
it's required to know about the security group and subnets within
the services should be launched. The following steps assumes
some experience with the AWS cloud environment and does not
deeply explain the concepts used outside of the scope of the {CB}
setup.

Fetch the security group ID as follows:

.. code:: bash

   aws ec2 describe-security-groups

Fetch the subnet IDs from available regions as follows:

.. code:: bash

   aws ec2 describe-subnets

Create Cluster
--------------

1. **Launch Amazon MSK:**

   Create the file :file:`cb-msk-setup.json` with the following content:

   .. code:: json

      {
          "InstanceType": "kafka.t3.small",
          "BrokerAZDistribution": "DEFAULT",
          "SecurityGroups": [
              "sg-MySecuritGroupId"
          ],
          "StorageInfo": {
              "EbsStorageInfo": {
                  "VolumeSize": 1
              }
          },
          "ClientSubnets": [
              "subnet-MySubnetIdRegionX",
              "subnet-MySubnetIdRegionY"
          ]
      }

   Start the messaging API as follows:

   .. code:: bash

      aws kafka create-cluster \
          --cluster-name "cloud-builder" \
          --broker-node-group-info file://cb-msk-setup.json \
          --encryption-info EncryptionInTransit={ClientBroker="PLAINTEXT"} \
          --kafka-version "2.6.2" \
          --number-of-broker-nodes 2

      ClusterArn=$(
          aws kafka list-clusters --cluster-name-filter cloud-builder | \
          grep ClusterArn | cut -f4 -d\"
      )

   .. note::

      The `create-cluster` call describes itself with a `ClusterArn` value
      which gets stored in the *$ClusterArn* shell variable. This value is
      needed for any operation to retrieve information from the MSK service
   
   The startup of the MSK service can take several minutes.
   During that time call the following command to fetch the
   zookeeper connection string. Please note as long as the
   cluster is in state `CREATING` there will be no zookeeper
   connection string printed:

   .. code:: bash

      aws kafka describe-cluster --cluster-arn ${ClusterArn}

   .. warning::

      Do not continue until there is a ZookeeperConnectString

2. **Checkout the CB git repository:**

   For provisioning of the cluster some helper scripts are provided
   in the git sources of {CB}

   .. code:: bash

      git clone https://github.com/OSInside/cloud-builder.git
 
3. **Launch the Control Plane, Collector(RepoServer) and Runners(2):**

   The simple cluster as described here consists out of a
   control plane, two runners and one collector which serves
   as the repo server. To start these instances edit the file
   :file:`provision_helper/cb_run_cluster_instances` from the
   git checkout and update the following setting to
   match your AWS EC2 cloud service:

   .. code:: bash

      # USER SETTINGS
      # Name of ssh key pair which you have registered in EC2
      key_name=ms

   Once done create the instances as follows:

   .. code:: bash

      provision_helper/cb_run_cluster_instances

   .. warning::

      Do not continue after all instances are in `Running` state

4. **Provision {CB} Services:**

   To provision the cluster edit the file
   :file:`provision_helper/cb_provision_cluster` and update the
   following settings to match your AWS EC2 cloud service:

   .. code:: bash

      # USER SETTINGS:
      # Path to private key which allows access to your EC2 instances
      ssh_pkey_path=${HOME}/.ssh/id_ec2

      # Path to source repo with your packages/images
      source_repo="https://github.com/OSInside/cloud-builder-packages.git"

   Once done provision the cluster as follows:

   .. code:: bash

      provision_helper/cb_provision_cluster

5. **Setup cb-ctl:**

   To work with the cluster the `cb-ctl` utility needs to be
   configured. Edit the file :file:`provision_helper/cb_setup_cb_ctl`
   and update the following settings to match your AWS EC2
   cloud service:

   .. code:: bash

      # USER SETTINGS:
      # Path to private key which allows access to your EC2 instances
      ssh_pkey_path=${HOME}/.ssh/id_ec2

   Once done call:

   .. code:: bash

      provision_helper/cb_setup_cb_ctl

   .. note::

      The setup of `cb-ctl` uses the `use_control_plane_as_proxy`
      configuration setting. This is the easiest way to connect to the
      cluster and uses the control plane as a proxy through SSH. However,
      this method is also the least performant one. For a production use
      either work with `cb-ctl` directly from the control plane or create
      a VPN connection to the VPC running in the cloud.

6. **Build A thing:**

   Finally use your {CB} cluster to build something. In this setup method
   the example git repo `https://github.com/OSInside/cloud-builder-packages`
   was used. You don't have to check it out to send build requests to the
   cluster but it makes the work easier because you can read the git and
   see how the packages are setup and which parameters needs to be passed
   to `cb-ctl`. To build the lovely `xclock` package for SUSE Tumbleweed
   call the following:

   .. code:: bash

      cb-ctl --build-package xclock --project-path MS \
          --arch x86_64 --dist TW --runner-group fedora

      cb-ctl --build-log xclock --project-path MS --keep-open \
          --arch x86_64 --dist TW

   Once done the repository with the package will appear on the collector.
   Point your preferred web browser to the collector instance as
   follows:

   .. code:: bash

      RepoServer=$(
          aws ec2 describe-instances --filters "Name=tag-value,Values=cb-collect" | \
          grep -m 1 PublicDnsName | cut -f4 -d\"
      )

      firefox http://${RepoServer}

   .. note::

      This requires the HTTP/HTTPS port to be opened in the security
      group assigned to the collector instance !

   The URL on the collector (aka RepoServer) can also be used in package
   managers to fetch and install the package(s).

   .. warning::

      As of today the packages and repositories created by {CB} are
      not signed.
