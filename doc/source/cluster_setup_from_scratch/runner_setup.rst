.. _runner-setup:

Runner Setup
============

A runner instance for {CB} is a machine that actually builds
packages. The produced binaries stays on that machine and can
be fetched on demand for further processing. The runner must
be configured for a specific runner group. The runner group
name matches the name of the message broker queue/topic name such
that only package build requests for this runner group are
handled by the associated runner(s). There must be at least
one runner for each runner group. If there are more runners
the produced build requests will be evenly distributed across
the available runners. This is how {CB} scales with the
amount of packages to build.

In the example setup of the control plane, the runner group
message topics `suse` and `fedora` were created. In addition
each of the runner groups was expected to serve 2 runners.
On the basis of this build power 4 runner instances must be
created and configured as follows:

1. **Start runner instances**

   For the `fedora` runner group the Fedora distribution
   is used. For the `suse` runner group the Leap distribution
   is used.

   .. code:: bash

      leap_15_3_ami=ami-0b4f49bedf96b14c9
      user_leap=ec2-user

      fedora_34_ami=ami-0b2a401a8b3f4edd3
      user_fedora=fedora

   .. note::

      Runner instances requires storage RAM and CPU power.
      In the cloud all of these components are cost factors.
      With {CB} it's possible to differentiate runner groups
      which can be designed such that there are some powerful
      and some less powerful machines. For package and/or
      image builds which are known to consume a lot of resources
      a runner group can be used that meets these requirements.
      That way the costs can be balanced.

2. **Install {CB} on the runners**

   Login to each of the created Leap runner instances and install
   {CB} as follows:

   .. code:: bash

      ssh -i PathToPkeyMatchingMySSHKeyPairName \
          ${user_leap}@InstanceIP

      sudo zypper addrepo https://download.opensuse.org/repositories/Virtualization:/Appliances:/CloudBuilder/openSUSE_Leap_15.3 cloud-builder
      sudo zypper install python3-cloud_builder

   Login to each of the created Fedora runner instances and install
   {CB} as follows:

   .. code:: bash

      ssh -i PathToPkeyMatchingMySSHKeyPairName \
          ${user_fedora}@InstanceIP

      sudo dnf config-manager \
          --add-repo https://download.opensuse.org/repositories/Virtualization:/Appliances:/CloudBuilder/Fedora_34 \
          --enable --nogpgcheck
      sudo dnf install python3-cloud_builder

   .. note::

      As shown above access to the runners is performaed via `ssh`
      The username to access machines in the cloud can be different
      compared to the used distribution. In the above example the
      Fedora based instance provides the `fedora` user, whereas the
      Leap machines provides the `ec2-user` user. This aspect needs
      to be taken into account when running instances in the cloud.

   .. note:: selinux

      Fedora systems uses selinux. For building packages and images
      the security policy could prevent required actions to complete
      like the creation of a new rpm database in a new root directory.
      To prevent this make sure selinux is not enforced by calling:
      `sudo setenforce 0`
      
3. **Create and setup the cb-collect user**

   In cloud environments the distributors publish cloud images with
   different predefined user configurations. For example on
   Fedora instances ssh login is used via `fedora@IP` whereas on
   Leap instances the user setup is `ec2-user@IP`. Most probably
   the username will be different on any distribution. As {CB}
   runners can be instances from different distributions to allow
   utilizing the native distribution tools to build packages, it
   is needed to generalize the user and access permissions which
   are used to access runners for collecting build results or for
   fetching build information.

   1. Login to the control plane.

      See :ref:`control-plane-setup` for details

   2. Fetch the `cb-collect` public and private SSH keys and
      logout from the control plane.

      .. code:: bash

         # public key
         cat ~/.ssh/id_cb_collect.pub

         # private key
         cat ~/.ssh/id_cb_collect

         exit

   3. Create and authorize the `cb-collect` user on this runner.

      .. code:: bash

         sudo -i
         useradd -d /home/cb-collect -m cb-collect
         su -l cb-collect
         mkdir -m 0700 .ssh
         touch .ssh/authorized_keys
         chmod 600 .ssh/authorized_keys
         touch .ssh/id_cb_collect
         chmod 600 .ssh/id_cb_collect

         vi .ssh/authorized_keys

           Copy & Paste the SSH pubkey as it was printed on the
           console in step 2. and safe the file

         vi .ssh/id_cb_collect

           Copy & Paste the SSH private key as it was printed on the
           console in step 2. and safe the file

         exit
         echo "cb-collect ALL=NOPASSWD: ALL" >> /etc/sudoers
         exit

4. **Setup broker connection and runner group on the runners**

   Login to each of the created runner instances and create
   the file :file:`/etc/cloud_builder_broker.yml` as follows:

   .. code:: bash

      sudo vi /etc/cloud_builder_broker.yml

   Place the following content:

   .. code:: yaml

      broker:
        host: BootstrapServersString
      this_host: external_IP_or_Hostname_of_this_instance

   See the '**Configure** `cb-ctl`' list item in the :ref:`control-plane-setup`
   for details how to obtain the broker credentials.

   * Add the following content on the Leap runners only

     .. code:: yaml

        runner:
          group: suse

   * Place the following content on the Fedora runners only

     .. code:: yaml

        runner:
          group: fedora

5. **Setup runner services configuration**

   On the runner several {CB} services like cb-fetch-once, cb-info
   or cb-scheduler will be started. All of these services reads
   configuration parameters from the file :file:`/etc/cloud_builder`
   Login to each of the created runner instances and setup the
   following settings:

   **git package source connection:**
     The below setting is the default after install of {CB}.
     The used CB_PROJECT git repository is the {CB} provided example git
     repo containing some arbitrary package sources. It only serves the
     purpose to let users test and run {CB}. For production
     change this value to your git project

     .. code:: bash

        CB_PROJECT="https://github.com/OSInside/cloud-builder-packages.git"

   **package/image build limit:**
     Every runner comes with a build limit. This is the number
     of simultaneously allowed build processes. If the limit is hit
     the runner closes its connection to the message broker until the
     number is below the maximum. For Apache kafka the close of the
     connection of a consumer will cause a rebalance of all other still
     connected consumers. This is an expensive operation and should be
     avoided. The {CB} set maximum of 10 package builds at the same time
     is relatively conservative. It depends on the selected instance
     type/memory and disk space to select an appropriate value. If in
     doubt give it a try with the default setting, but keep in mind
     about this value, especially for production use.

     .. code:: bash

        CB_BUILD_LIMIT=10

   **runner count:**
     The {CB} runner count specifies the number of runners that exists
     in the cluster. This information will be used in services which
     asks for information from the cb-info service. Each runner provides
     an info service. On request multiple info services could respond
     with information about a package/image. As the requester doesn't
     know how many answers completes the record, the default behavior
     is to wait for a configurable time of silence on the response
     queue before handing control back to the user and working
     on the results.

     This can lead to an unneeded amount of waiting time for
     the user. There is also always the risk that the wait time
     was not long enough to retrieve all answers from the
     cb-info services in the system.

     If the information about the number of runners in the
     cluster is provided, this value will be used to count the
     number of answers and if that number equals the number
     of runners it is clear that there can't be more answers
     which leads the reading code to get back to the user
     instead of staying blocked waiting for the timeout.

     If the runner count is configured, it's also required that all
     cb-info services are configured to respond to any request even
     if there is no information available for the requested package
     or image.

     .. code:: bash

        CB_RUNNERS=2
        CB_INFO_RESPONSE_TYPE="--respond-always"

     The default value of 0 runners indicates there is no
     knowledge about the amount of runners in the system and that
     leads to the timeout based behavior as explained above

6. **Start** `cb-fetch-once` **service**

   Login to each of the created runner instances and fetch
   the package source git once as follows:

   .. code:: bash

      sudo systemctl start cb-fetch-once

   This will clone the configured CB_PROJECT git repo once on the
   system. The `cb-scheduler` service cares for the repo update via
   `git pull` on demand

7. **Start** `cb-scheduler` **and** `cb-info` **services**

   Login to each of the created runner instances and start
   the scheduler and info services as follows:

   .. code:: bash

      sudo systemctl start cb-scheduler
      sudo systemctl start cb-info

Congrats, the {CB} package build backend is now running and can
build packages for Fedore/RHEL and SUSE/SLES based packages.
There are two runners available for each of these vendors.

Learn how to build the first package next: :ref:`request_package_build`
