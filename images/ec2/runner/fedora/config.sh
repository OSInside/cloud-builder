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
baseInsertService cb-fetch-once
baseInsertService cb-scheduler
baseInsertService cb-info

# Add cb-collect to sudoers
echo "cb-collect ALL=NOPASSWD: ALL" >> /etc/sudoers

# Set runner info service to respond always
sed -ie "s@CB_INFO_RESPONSE_TYPE=.*@CB_INFO_RESPONSE_TYPE=\"--respond-always\"@" \
    /etc/cloud_builder

# Fix permissions
chown -R cb-collect /home/cb-collect
chgrp -R cb-collect /home/cb-collect

#======================================
# Setup default target, multi-user
#--------------------------------------
baseSetRunlevel 3
