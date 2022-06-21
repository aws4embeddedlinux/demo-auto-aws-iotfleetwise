# AGL EW22 Demo Image

## Preparation

You will need to complete all preparation steps to complete all the
sections in this tutorial successfully.

1. Perform all workstation preparation steps as defined in the Yocto
   Mega Manual.
2. An [AWS Account](https://aws.amazon.com/free) and an [AWS Identity
   and Access Management (IAM)](https://aws.amazon.com/iam/) with
   authorization to run the [IoT Greengrass
   Tutorial](https://docs.aws.amazon.com/greengrass/latest/developerguide/gg-gs.html)
   in the context of your logged in [IAM
   User](https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction_identity-management.html).

## Prepare, invoke, and flash the build

Due to the size of this build, the build environment was defined in the AWS Cloud using a c5.18xlarge instance type. Remember that in the AWS Cloud you pay for what you use, so to be thrifty consider stopping or terminating your instance after performing the build tasks.

1. Launch the EC2 instance with the Ubuntu 18.04 AMI.

2. Login to the EC2 instance with ssh and prepare system updates.
   
   ```bash
   sudo apt-get update
   sudo apt-get -y upgrade
   ```
3. In the EC2 instance terminal, perform steps on the [Downloading AGL
   Software](https://docs.automotivelinux.org/en/master/#0_Getting_Started/2_Building_AGL_Image/2_Downloading_AGL_Software/)
       page.
   
   The command line steps we used are here.  Please reference the
   documentation if you would like an explanation of steps.
   
   ```bash
   export PRJ_TOP=$(pwd)
   export AGL_TOP=$HOME/AGL
   echo 'export AGL_TOP=$HOME/AGL' >> $HOME/.bashrc
   mkdir -p $AGL_TOP
   
   mkdir -p $HOME/bin
   export PATH=$HOME/bin:$PATH
   echo 'export PATH=$HOME/bin:$PATH' >> $HOME/.bashrc
   curl https://storage.googleapis.com/git-repo-downloads/repo > $HOME/bin/repo
   chmod a+x $HOME/bin/repo
   ```
   We will be using the Merlin release since it aligns with
   the Yocto Project **dunfell** LTS release.

   ```bash
   cd $AGL_TOP
   mkdir marlin
   cd marlin
   repo init -b marlin -m marlin_13.0.1.xml -u https://gerrit.automotivelinux.org/gerrit/AGL/AGL-repo
   repo sync
   ```

4. In our build, we will be building for the AGL base image. To set this up easily,
initialize the build environment with the new `aglsetup.sh` utility.
Its full use is described in the [Initializing Your Build Environment](https://docs.automotivelinux.org/en/master/#0_Getting_Started/2_Building_AGL_Image/3_Initializing_Your_Build_Environment/)
section of the AGL documentation.

   ```bash
   cd $AGL_TOP/marlin
   source meta-agl/scripts/aglsetup.sh -m s32g274ardb2 agl-basesystem
   ```

5. At this point, the base image is configured but we need to add AWS
   IoT Greengrass and dependencies.
   
   ```bash
   cd $AGL_TOP/marlin
   git clone -b dunfell https://github.com/aws/meta-aws
   bitbake-layers add-layer $AGL_TOP/marlin/external/meta-openembedded/meta-networking
   bitbake-layers add-layer $AGL_TOP/marlin/external/meta-openembedded/meta-python
   bitbake-layers add-layer $AGL_TOP/marlin/meta-aws
   ```
6. Edit the passwd and group file in meta-agl-core to overcome
   https://github.com/aws/meta-aws/issues/75

   ```bash
   echo "ggc_group::10000:" >> $AGL_TOP/marlin/meta-agl/meta-agl-core/files/group
   echo "ggc_user::10000:10000:::" >> $AGL_TOP/marlin/meta-agl/meta-agl-core/files/passwd
   ```

7. Create the Greengrass Thing and append the following to `local.conf` to add greengrass.

   ```bash
   cd $PRJ_TOP
   THING_NAME=agl-demo THING_GROUP_NAME=ew22 AWS_DEFAULT_REGION=eu-central-1 ./gg-env-setup.sh

   cat ./local.conf >> $AGL_TOP/marlin/build/conf/local.conf
   ```
This will generate the certificates and add necessery variables to the `local.conf`.

8. Now we need to copy the certs so they get included into the build

   ```bash
   cp ./certs/* $AGL_TOP/marlin/meta-aws/recipes-iot/aws-iot-greengrass/files/
   ```

9. Invoke the build.

   ```bash
   source $AGL_TOP/AGL/marlin/build/agl-init-build-env 
   bitbake agl-image-minimal 
   ```

10. This should produce an sdcard image which than can be flased to the device. Youi can also upload it to the S3 bucket in order to retrive it later

   ```bash
    aws s3 cp $AGL_TOP/marlin/build/tmp/deploy/images/s32g274ardb2/agl-image-minimal-s32g274ardb2.sdcard <desired s3 bucket>
   ```
   
