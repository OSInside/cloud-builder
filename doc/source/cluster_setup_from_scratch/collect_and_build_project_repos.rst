.. _collect_and_build_project_repos:

Collect and Build Project Repos
===============================

Building the packages on the runner(s) is the foundation of
the {CB} project. However, first the possibility to create
and publish package repositories creates real value to it.
The `cb-collect` service implements the creation of package
repositories by allowing the runners to sync their build results
to the collector. `cb-collect` periodically runs over this
data and creates package metadata such that package managers
can consume them.

This chapter describes how to setup `cb-collect` in combination
with an `apache` web-server to serve the `cb-collect` created
repositories. Let's call this instance the `reposerver`.

Create and Setup the reposerver instance
----------------------------------------

1. **Start reposerver instance**

   For the reposerver there is no real requirement to use a
   specific linux distribution. In this document the Leap
   distribution is used. In AWS EC2 the following AMI ID
   can be used to run the instance:

   .. code:: bash

      leap_15_3_ami=ami-0b4f49bedf96b14c9
      username=ec2-user

   .. note::

      The reposerver instance requires a good network connection
      as well as enough storage capacity to store the repository
      data. Therefore the selected `t2.micro` instance type might
      not be sufficient depending on what magnitude the {CB}
      services are used

2. **Install {CB} on the reposerver**

   Login to the reposerver instance and install {CB} as follows:

   .. code:: bash

      ssh -i PathToPkeyMatchingMySSHKeyPairName \
          ${username}@RepoServerInstanceIP

      sudo zypper addrepo https://download.opensuse.org/repositories/Virtualization:/Appliances:/CloudBuilder/openSUSE_Leap_15.3 cloud-builder
      sudo zypper install python3-cloud_builder

3. **Setup cb-collect service configuration**

   Still logged in on the reposerver the file :file:`/etc/cloud_builder`
   contains service parameters which needs to be setup as follows:

   **git package source connection**
     The below setting is the default after install of {CB}.
     The used CB_PROJECT git repository is the {CB} provided example git
     repo containing some arbitrary package sources. It only serves the
     purpose to let users test and run {CB}. For production
     change this value to your git project

     .. code:: bash

        CB_PROJECT="https://github.com/OSInside/cloud-builder-packages.git"

4. **Allow SSH access from runners**

   To allow the runners to push their build results to the
   collector it's required to allow the runners SSH pub key
   in the :file:`authorized_keys` file of the reposerver.

   During the setup of the control plane a SSH keypair has already
   been created and rolled out to the runners. The same keypair
   as present on the control plane can now also be used on the
   reposerver as follows:

   1. Login to the control plane from a new terminal session.

      See :ref:`control-plane-setup` for details

   2. Fetch the `cb-collect` public SSH key.

      .. code:: bash

         cat ~/.ssh/id_cb_collect.pub

         ==> Copy the SSH public key into the Copy/Paste buffer

         exit

      Add the SSH public key to the :file:`authorized_keys` file
      on the **reposerver** as follows:

      .. code:: bash

         vi ~/.ssh/authorized_keys

         ==> Paste the SSH public key from the Copy/Paste buffer


5. **Attach an EBS volume to the reposerver**

   To store and backup the repository data an extra block storage
   volume should be attached to the server.

   * Follow the documentation from here to attach a new volume:
     https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-attaching-volume.html
       
   * Create the `XFS` filesystem on the new volume and mount it to
     :file:`/srv/www` on the reposerver. Read the following documentation
     to understand how to make the volume available:
     https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-using-volumes.html

6. **Setup runners to sync their results to the collector**

   In the setup of the runners the settings to connect to the
   collector were not configured. This must be done now as follows:

   1. Login to a runner instance

   2. On the runner instance edit the file :file:`/etc/cloud_builder`
      and set/update the following parameters:

      .. code:: bash

         CB_COLLECT_REPO_SERVER="RepoServerInstanceIP"
         CB_SSH_USER="ec2-user"

      .. note::

         Make sure the user(ec2-user in this example) also has
         permissions to write data in :file:`/srv/www/`. This is
         the place the runners will upload its data.

   3. Restart the scheduler

      .. code:: bash

         systemctl restart cb-scheduler

   4. Repeat this steps for all runners of interest

7. **Start** `cb-collect` **service**

   Still logged in on the reposerver, start the `cb-collect` service
   as follows:

   .. code:: bash

      sudo systemctl start cb-collect

   The service will immediately start to build repositories from
   the available package data. Package and images arrives through
   build requests.

Setup Apache to Serve the Repos
-------------------------------

All repos created by the `cb-collect` service are now available
and managed on the local system. To consume the repos the `Apache`
web server is used. The following describes a very simple setup
for `Apache` to serve the :file:`/srv/www/projects/projects`
contents.

.. note::

   The following setup instructions for `Apache` are valid if
   the reposerver is based on the Leap distribution. In case
   another distribution was used, adaptions to the information
   below are likely.

1. **Install** `Apache`

   .. code:: bash

      sudo zypper in apache2

2. **Setup Apache DocumentRoot**

   Edit the file :file:`/etc/apache2/httpd.conf` and place the
   following content at the end of the file:

   .. code:: bash

      DocumentRoot "/srv/www/projects/projects"

      <Directory "/srv/www/projects/projects">
          Options All Indexes FollowSymLinks
          AllowOverride None
          Require all granted
      </Directory>

   .. note::

      For a real production setup including https access,
      more config steps are needed. In addition the `Apache`
      documentation recommends to place setup instructions
      in separate files and only include them in the master
      configuration. This all makes sense, so please consider
      the above as an example to get started.
       
3. **Start** `Apache`

   .. code:: bash

      sudo systemctl start apache2

4. **Open HTTP port**

   By default instances in the cloud blocks all inbound ports.
   To access the server the HTTP port must be opened for
   incomming connections. To do this add a new HTTP(80) inbound rule
   in the used security group of the reposerver instance. The
   documentation from here: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/authorizing-access-to-an-instance.html helps with that task

5. **Access the reposerver**

   Open a web browser and place the following URL:

   .. code:: bash

      http://RepoServerInstanceIP
