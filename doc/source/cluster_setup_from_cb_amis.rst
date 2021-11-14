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

For a simpler and straight forward way to setup {CB} in Amazon,
three pre-configured AMIs were registered. One to create an
instance for the `control-plane`, one for creating a `collector`
instance and one to create one or more `runner` instances. All
AMIs are based on the `Fedora` distribution and comes with many
tools from other distributions pre-installed, such that the runners
can build packages and images for a variety of different
distributions.

.. note::

   I need to come up with the aws sequence of commands to run
   the cluster. Stay tuned :)
