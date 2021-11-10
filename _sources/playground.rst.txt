.. _playground:

Playground
==========

This chapter contains just some sort of brain dump of things
I tried out, or other people can try out. An area for crazy
ideas and unfinished stuff.

Remember to have fun :)


Building Debian Packages
~~~~~~~~~~~~~~~~~~~~~~~~

I was testing this and came across the following steps to build debs
  
* A Debian based host is needed. To have all the tools and a native
  environment I think the runner should be a Debian host. It doesn't
  matter what it is, unstable, ubuntu, debian ...

* Add the Staging repo to :file:`/etc/apt/sources.list.d/cloud_builder.list`

  .. code:: bash

     deb [trusted=yes check-valid-until=no] https://download.opensuse.org/repositories/Virtualization:/Appliances:/Staging/xUbuntu_20.04/ /

  .. code:: bash

     $ sudo apt update
     $ sudo apt install python3-cloud-builder

* Checkout the example packages repo

  .. code:: bash

     $ git clone https://github.com/OSInside/cloud-builder-packages.git

* And run a local build

  I put a debbuild prepared spec file for the python-kiwi packages
  as an example. So this build will use debbuild which can consume
  the information from an rpm spec file and create debs out of it.
    
  .. note::

     deb build with debbuild will not be accepted by the comunity
     building with sources as they exist on https://salsa.debian.org/
     and a good debian/ directory with all dpkg metadata should also
     be buildable via {CB}

  .. code:: bash

     $ cd cloud-builder-packages/projects/MS/python-kiwi

     $ sudo cb-ctl --build-package-local --dist focal

Simple Cluster Setup
~~~~~~~~~~~~~~~~~~~~

Using Kafka as a service produces costs. In Amazon the MSK service
cannot be simply stopped and restarted, it can only be deleted and
created from scratch. On deletion the MSK topics and its configuration
will be gone and needs to be reconfigured after startup. For this
process several options exists. One of the simplest ist a shell
script called from the control plane instance and after creation of
the MSK service via the web console or the `aws` tool using
the AWS API.

Please find an implementation in shell to startup and configure
a {CB} cluster when all instances in the cloud and MSK are running
here:

* https://github.com/OSInside/cloud-builder/tree/master/images/ec2/control-plane/root/home/fedora
