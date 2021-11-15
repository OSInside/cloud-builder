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

   $ aws ec2 describe-security-groups

Fetch the subnet IDs from available regions as follows:

.. code:: bash

   $ aws ec2 describe-subnets

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

      $ ClusterArn=$(
          aws kafka create-cluster \
              --cluster-name "cloud-builder" \
              --broker-node-group-info file://cb-msk-setup.json \
              --encryption-info EncryptionInTransit={ClientBroker="PLAINTEXT"} \
              --kafka-version "2.6.2" \
              --number-of-broker-nodes 2 | \
          grep ClusterArn | cut -f4 -d\"
        )

   .. note::

      The `create-cluster` call will respond with a `ClusterArn` value
      which gets stored in the *$ClusterArn* shell variable. This value is
      needed for any operation to retrieve information from the MSK service
   
   The startup of the MSK service can take several minutes.
   During that time call the following command to fetch the
   zookeeper connection string. Please note as long as the
   cluster is in state `CREATING` there will be no zookeeper
   connection string printed:

   .. code:: bash

      $ aws kafka describe-cluster --cluster-arn ${ClusterArn}

   .. warning::

      Do not continue until there is a ZookeeperConnectString
 
2. **Launch the Control Plane:**

   Start the `control plane` as follows:

   .. code:: bash

      $ aws ec2 run-instances \
          --count 1 \
          --image-id ami-0641c1ac6db821f59 \
          --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=cb-control-plane}]' \
          --instance-type t2.micro \
          --key-name MySSHKeyPairName

3. **Launch the Collector:**

   Start the `collector` as follows:

   .. code:: bash

      $ aws ec2 run-instances \
          --count 1 \
          --image-id ami-0a33de229d8c3a832 \
          --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=cb-collect}]' \
          --instance-type t2.micro \
          --key-name MySSHKeyPairName

4. **Launch the Runners:**

   Start the `runners` as follows:

   .. code:: bash

      $ for name in cb-runner-1 cb-runner-2;do
          aws ec2 run-instances \
              --count 1 \
              --image-id ami-0beda72d2abd9e15a \
              --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$name}]" \
              --block-device-mapping "DeviceName=/dev/xvda,Ebs={VolumeSize=100}" \
              --instance-type t2.micro \
              --key-name MySSHKeyPairName
        done

5. **Provision {CB} Services:**

   Create the script :file:`setup_cb.cfg.sh` and place the following content

   .. code:: bash

      #!/bin/bash

      set -e

      ClusterArn=$(
          aws kafka list-clusters --cluster-name-filter cloud-builder | \
          grep CLUSTERINFOLIST | cut -f2 -d" "
      )
      BootstrapBrokerString=$(
          aws kafka get-bootstrap-brokers --cluster-arn ${ClusterArn} | \
          grep BootstrapBrokerString | cut -f4 -d\"
      )
      ZookeeperConnectString=$(
          aws kafka describe-cluster --cluster-arn ${ClusterArn} | \
          grep ZookeeperConnectString | cut -f4 -d\"
      )
      CBControlPlane=$(
          aws ec2 describe-instances --filters "Name=tag-value,Values=cb-control-plane" | \
          grep -m 1 PrivateDnsName | cut -f4 -d\"
      )
      CBCollect=$(
          aws ec2 describe-instances --filters "Name=tag-value,Values=cb-collect" | \
          grep -m 1 PrivateDnsName | cut -f4 -d\"
      )
      CBRunners=""
      for name in cb-runner-1 cb-runner-2;do
          runner=$(
              aws ec2 describe-instances --filters "Name=tag-value,Values=${name}" | \
              grep -m 1 PrivateDnsName | cut -f4 -d\"
          )
          CBRunners="${CBRunners} ${runner}"
      done

      cat <<EOF
      # ZookeeperConnectString
      ZookeeperConnectString="${ZookeeperConnectString}"

      # BootstrapBrokerString
      BootstrapServersString="${BootstrapBrokerString}"

      # internal host name of the control plane
      control_plane="${CBControlPlane}"

      # git source repo for packages/images
      source_repo="https://github.com/OSInside/cloud-builder-packages.git"

      # runner group names in the form "name_a name_b ..." 
      runner_topics="fedora"

      # internal host name of the collector
      collector="${CBCollect}"

      # internal host names of the runners in the form "host_a host_b ..."
      runners="$(echo ${CBRunners})"
      EOF

   Create the file :file:`setup_cb.cfg` as follows:

   .. code:: bash

      $ bash setup_cb.cfg.sh > setup_cb.cfg

   Copy the setup file to the `control-plane` and provision the cluster

   .. code:: bash

      $ scp -i PathToPkeyMatchingMySSHKeyPairName \
          setup_cb.cfg fedora@ControlPlanePublicInstanceIP:~

      $ ssh -i PathToPkeyMatchingMySSHKeyPairName \
          fedora@ControlPlanePublicInstanceIP ~fedora/setup_cb
