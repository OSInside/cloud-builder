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

# Delete welcome page
rm -f /etc/httpd/conf.d/welcome.conf

# Activate services CB
baseInsertService cb-collect

baseInsertService httpd

# Create reposerver root
mkdir -p /srv/www/projects/projects
chown -R cb-collect /srv/www/projects
chgrp -R cb-collect /srv/www/projects

# Add cb-collect to sudoers
echo "cb-collect ALL=NOPASSWD: ALL" >> /etc/sudoers

# Fix permissions
chown -R cb-collect /home/cb-collect
chgrp -R cb-collect /home/cb-collect

#======================================
# Setup default target, multi-user
#--------------------------------------
baseSetRunlevel 3
