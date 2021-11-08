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
baseInsertService cb-fetch

# Fix permissions
chown -R fedora /home/fedora
chgrp -R fedora /home/fedora

#======================================
# Setup default target, multi-user
#--------------------------------------
baseSetRunlevel 3
