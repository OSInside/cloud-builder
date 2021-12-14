#!/bin/bash
# Helper script to upload and register x86_64 cloud builder
# images to AWS EC2 for quick setup of a CB build cluster

rm -rf binaries
mkdir -p binaries

pushd binaries

wget https://download.opensuse.org/repositories/Virtualization:/Appliances:/CloudBuilder:/EC2:/fedora/images/CB-RunnerFedora.x86_64.raw.xz

popd

image=binaries/CB-RunnerFedora.x86_64.raw.xz

desc="$(basename $image | cut -f1 -d.)"-x86
name="${desc}-v$(date +%Y%m%d)"

ec2uploadimg \
    -a ms -f ~ms/.ec2/ec2utils.conf \
    --grub2 \
    -m x86_64 \
    -n ${name} \
    --sriov-support \
    --ena-support \
    -r eu-central-1 \
    --description "${desc}" \
    --verbose \
    -B ssd \
${image}
