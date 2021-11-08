test -f /.kconfig && . /.kconfig

echo "Configure image: [$kiwi_iname]..."

# sysconfig settings
echo '# Support dynamic multinic configuration' \
    >> /etc/sysconfig/network/config
net_modules="cloud-netconfig dns-resolver dns-bind dns-dnsmasq nis ntp-runtime"
echo "NETCONFIG_MODULES_ORDER=\"$net_modules\"" \
    >> /etc/sysconfig/network/config

# Setup policy kit
[ -x /sbin/set_polkit_default_privs ] && /sbin/set_polkit_default_privs

# Disable password based login via ssh
ssh_option=ChallengeResponseAuthentication
sed -i "s/#${ssh_option} yes/${ssh_option} no/" \
    /etc/ssh/sshd_config

# Activate services
suseInsertService boot.device-mapper
suseInsertService haveged
suseInsertService sshd
suseInsertService cloud-netconfig.timer

# Activate services CB
suseInsertService cb-fetch-once
suseInsertService cb-collect

if [ "$kiwi_profiles" = "EC2-HVM" ];then
    # Activate/De-activeta services
    suseInsertService chronyd
    suseInsertService cloud-init-local
    suseInsertService cloud-init
    suseInsertService cloud-config
    suseInsertService cloud-final
fi
