#!/bin/bash
set -e

test -f /.kconfig && . /.kconfig

echo "Configure image: [$kiwi_iname]..."

# Disable password based login via ssh
ssh_option=ChallengeResponseAuthentication
sed -i "s/#${ssh_option} yes/${ssh_option} no/" \
    /etc/ssh/sshd_config

# Activate services
baseInsertService dbus-broker
baseInsertService NetworkManager
baseInsertService sshd
baseInsertService chronyd
baseInsertService cloud-init-local
baseInsertService cloud-init
baseInsertService cloud-config
baseInsertService cloud-final

# Activate services CB
baseInsertService cb-collect
baseInsertService httpd

# Set collect pkey reference
sed -ie "s@CB_SSH_PKEY=.*@CB_SSH_PKEY=\"/root/.ssh/id_cb_collect\"@" \
    /etc/cloud_builder

# Set collect user reference
sed -ie "s@CB_SSH_USER=.*@CB_SSH_USER=\"cb-collect\"@" \
    /etc/cloud_builder


# Create reposerver root
mkdir -p /srv/www/projects

#======================================
# Setup default target, multi-user
#--------------------------------------
baseSetRunlevel 3
