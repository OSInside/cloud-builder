.. _collect_and_build_project_repos:

Collect and Build Project Repos
===============================

Building the packages on the runner(s) is the foundation of
the {CB} project. However, first the possibility to create
and publish package repositories creates real value to it.
The `cb-collect` service implements the creation of package
repositories by collecting the latest build results from
the runner(s) plus creation of the metadata information
such that package managers can consume them.

This chapter describes how to setup `cb-collect` in combination
with an `apache` web-server to serve the `cb-collect` created
repositories. Let's call this instance the `reposerver`.

Create and Setup the reposerver instance
----------------------------------------

1. **Start reposerver instance**

   For the reposerver there is no real requirement to use a
   specific linux distribution. It makes the setup procedure
   simpler to use a distribution for which {CB} packages are
   provided though. {CB} packages are available for Leap and
   Fedora at the moment. Thus let's go for Leap as a start
   and run a Leap 15.3 instance as follows:

   .. code:: bash

      $ leap_15_3_ami=ami-0b4f49bedf96b14c9

      $ aws ec2 run-instances \
          --image-id ${leap_15_3_ami} \
          --count 1 \
          --instance-type t2.micro \
          --key-name MySSHKeyPairName \
          --security-group-ids sg-MyGroup \
          --subnet-id subnet-MySubNet;
   
   .. note::

      The reposerver instance requires a good network connection
      as well as enough storage capacity to store the repository
      data. Therefore the selected `t2.micro` instance type might
      not be sufficient depending on what magnitude the {CB}
      services are used

2. **Install {CB} on the reposerver**

   Login to the reposerver instance and install {CB} as follows:

   .. code:: bash

      $ ssh -i PathToPkeyMatchingMySSHKeyPairName \
            ec2-user@RepoServerInstanceIP

      $ sudo zypper addrepo https://download.opensuse.org/repositories/Virtualization:/Appliances:/Staging/openSUSE_Leap_15.3 cloud-builder
      $ sudo zypper install python3-cloud_builder

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

   **runner count:**
     The {CB} runner count specifies the number of runners that exists
     in the cluster. This information will be used in cb-collect which
     asks for information from the cb-info service. Each runner provides
     an info service. On request multiple info services could respond
     with information about a package/image. As the requester doesn't
     know how many answers completes the record, the default behavior
     is to wait for a configurable time of silence on the response
     queue before handing control back to the collector and working
     on the results.

     This can lead to an unneeded amount of waiting time in the
     collector. There is also always the risk that the wait time
     was not long enough to retrieve all answers from the
     cb-info services in the system.

     If the information about the number of runners in the
     cluster is provided, this value will be used to count the
     number of answers and if that number equals the number
     of runners it is clear that there can't be more answers
     which leads the reading code to get back to the collector
     instead of staying blocked waiting for the timeout.

     .. code:: bash

        CB_RUNNERS=2

     The default value of 0 runners indicates there is no
     knowledge about the amount of runners in the system and that
     leads to the timeout based behavior as explained above

4. **Setup broker connection on the reposerver**

   Still logged in on the reposerver create the file
   :file:`/etc/cloud_builder_broker.yml` as follows:

   .. code:: bash

      sudo vi /etc/cloud_builder_broker.yml

   Place the following content:

   .. code:: yaml

      broker:
        host: BootstrapServersString
      this_host: external_IP_or_Hostname_of_this_instance

   See the '**Configure** `cb-ctl`' list item in the :ref:`control-plane-setup`
   for details how to obtain the broker credentials.

5. **Setup SSH access for collecting packages from runners**

   To allow the reposerver accessing data from the runners,
   it's required to SSH authorize the reposerver. In the
   setup of the control plane a SSH keypair has already
   been created to allow the control plane access to the
   runners. The same private key as present on the control
   plane can now also be used on the reposerver. This
   can be done as follows:

   1. Login to the control plane from a new terminal session.

      See :ref:`control-plane-setup` for details

   2. Fetch the `cb-collect` private SSH key and logout from the control plane.

      .. code:: bash

         $ cat ~/.ssh/id_cb_collect
         $ exit

   In the terminal session with the still active login session on
   the reposerver copy/paste the `cb-collect` SSH private key as
   follows:

   .. code:: bash

      $ mkdir -p -m 0700 /root/.ssh
      $ sudo touch /root/.ssh/id_cb_collect
      $ sudo chmod 600 /root/.ssh/id_cb_collect
      $ sudo vi /root/.ssh/id_cb_collect

        Copy & Paste the SSH private key as it was obtained
        in the former step and safe the file.

   Once done reference the path to the private key in the
   :file:`/etc/cloud_builder` setup file as follows:

   .. code:: bash

       $ sudo vi /etc/cloud_builder

       CB_SSH_PKEY="/root/.ssh/id_cb_collect"

6. **Attach an EBS volume to the reposerver**

   To store and backup the repository data an extra block storage
   volume should be attached to the server.

   * Follow the documentation from here to attach a new volume:
     https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-attaching-volume.html
       
   * Create the `XFS` filesystem on the new volume and mount it to
     :file:`/srv/www` on the reposerver. Read the following documentation
     to understand how to make the volume available:
     https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-using-volumes.html

7. **Setup user to be used for accessing the runners**

   In the setup of the runner a generic user to access the runner
   for build results and information was created. This user, by
   default, is called `cb-collect`. In the setup of the collector
   it's required to specify the user name which is allowed to
   access the runners as follows:

   .. code:: bash

       $ sudo vi /etc/cloud_builder

       CB_SSH_USER="cb-collect"

8. **Start** `cb-collect` **service**

   Still logged in on the reposerver, start the `cb-collect` service
   as follows:

   .. code:: bash

      $ sudo systemctl start cb-collect

   The service will immediately start to collect package results
   from the available runners. This is done by sending info requests
   which are read and worked on by the `cb-info` service. Therefore
   it's required that `cb-info` runs on all runners which are expected
   to provide data to be present in repositories.

   If there is response information for packages, `cb-collect`
   creates repositories in the same structure than the git repo
   is organized. For the example git tree this could look like
   the following example:

   .. code:: bash

      /srv/www/projects/projects/MS/...

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

      $ sudo zypper in apache2

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

      $ sudo systemctl start apache2

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
