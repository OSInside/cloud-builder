#!/bin/bash
# Helper script to upload and register x86_64 cloud builder
# images to AWS EC2 for quick setup of a CB build cluster

osc getbinaries \
    Virtualization:Appliances:CloudBuilder:EC2:fedora images x86_64

for image in binaries/*.raw.xz; do
    desc=$(basename $image | cut -f1 -d.)
    name=${desc}-v$(date +%Y%m%d)

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
done
