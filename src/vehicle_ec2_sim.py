from aws_cdk import (
    CfnOutput,
    Duration,
    Aws,
    aws_iam as iam,
    aws_ec2 as ec2
)
import cdk_aws_iotfleetwise as ifw
from constructs import Construct


class VehicleEc2Sim(Construct):
    def __init__(self, scope: Construct, id: str, vehicle: ifw.Vehicle, **kwargs):
        super().__init__(scope, id, **kwargs)

        vpc = ec2.Vpc.from_lookup(self, 'VPC', is_default=True)

        security_group = ec2.SecurityGroup(self, 'SecurityGroup',
                                           vpc=vpc,
                                           allow_all_outbound=True)

        security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(22), 'SSH access')
        security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.all_icmp(), 'ping')

        # EC2 role
        ec2_role = iam.Role(self, 'ec2Role',
                            assumed_by=iam.ServicePrincipal('ec2.amazonaws.com'),
                            managed_policies=[
                                iam.ManagedPolicy.from_aws_managed_policy_name(
                                    'AmazonSSMManagedInstanceCore'),
                                iam.ManagedPolicy.from_aws_managed_policy_name(
                                    'AdministratorAccess')
                            ])

        # Ubuntu 18.04 for Arm64
        machine_image = ec2.MachineImage.from_ssm_parameter(
            '/aws/service/canonical/ubuntu/server/18.04/stable/current/arm64/hvm/ebs-gp2/ami-id',
            os=ec2.OperatingSystemType.LINUX)

        key_name = self.node.try_get_context("key_name")
        # Create the Vehicle simulator
        instance = ec2.Instance(self, 'VehicleSim',
                                vpc=vpc,
                                instance_type=ec2.InstanceType('m6g.xlarge'),
                                machine_image=machine_image,
                                security_group=security_group,
                                key_name=key_name,
                                role=ec2_role,
                                vpc_subnets=ec2.SubnetSelection(
                                    subnet_type=ec2.SubnetType('PUBLIC')),
                                resource_signal_timeout=Duration.minutes(30))

        source_url = 'https://github.com/aws/aws-iot-fleetwise-edge.git'
        user_data = f'''\
            set -euo pipefail

            # Wait for any existing package install to finish
            i=0
            while true; do
                if sudo fuser /var/{{lib/{{dpkg,apt/lists}},cache/apt/archives}}/lock >/dev/null 2>&1; then
                    i=0
                else
                    i=`expr $i + 1`
                    if expr $i \>= 10 > /dev/null; then
                        break
                    fi
                fi
                sleep 1
            done

            # Upgrade system and reboot if required
            apt update && apt upgrade -y
            if [ -f /var/run/reboot-required ]; then
            # Delete the UserData info file so that we run again after reboot
            rm -f /var/lib/cloud/instances/*/sem/config_scripts_user
            reboot
            exit
            fi

            # Install helper scripts:
            apt update && apt install -y python3-setuptools
            mkdir -p /opt/aws/bin
            wget https://s3.amazonaws.com/cloudformation-examples/aws-cfn-bootstrap-py3-latest.tar.gz
            python3 -m easy_install --script-dir /opt/aws/bin aws-cfn-bootstrap-py3-latest.tar.gz
            rm aws-cfn-bootstrap-py3-latest.tar.gz

            # On error, signal back to cfn:
            error_handler() {{
                /opt/aws/bin/cfn-signal --success false --stack {Aws.STACK_NAME} \
                    --resource {instance.instance.logical_id} --region {Aws.REGION}
            }}
            trap error_handler ERR

            # Increase pid_max:
            echo 1048576 > /proc/sys/kernel/pid_max
            # Disable syslog:
            systemctl stop syslog.socket rsyslog.service
            # Remove journald rate limiting and set max size:
            printf "RateLimitBurst=0\nSystemMaxUse=1G\n" >> /etc/systemd/journald.conf

            # Install packages
            apt update && apt install -y git ec2-instance-connect htop jq unzip

            # Install AWS CLI:
            curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
            unzip awscliv2.zip
            ./aws/install
            rm awscliv2.zip

            # Download source
            cd /home/ubuntu
            if echo {source_url} | grep -q 's3://'; then
            sudo -u ubuntu aws s3 cp {source_url} aws-iot-fleetwise-edge.zip
            sudo -u ubuntu unzip aws-iot-fleetwise-edge.zip -d aws-iot-fleetwise-edge
            else
            sudo -u ubuntu git clone {source_url} aws-iot-fleetwise-edge
            fi
            cd aws-iot-fleetwise-edge
            
            # Install SocketCAN modules:
            ./tools/install-socketcan.sh --bus-count 1
            
            # Install CAN Simulator
            ./tools/install-cansim.sh --bus-count 1
            
            # Install FWE credentials and config file
            mkdir /etc/aws-iot-fleetwise
            echo -n "{vehicle.certificate_pem}" > /etc/aws-iot-fleetwise/certificate.pem
            echo -n "{vehicle.private_key}" > /etc/aws-iot-fleetwise/private-key.key
            ./tools/configure-fwe.sh \
            --input-config-file "configuration/static-config.json" \
            --output-config-file "/etc/aws-iot-fleetwise/config-0.json" \
            --vehicle-id {vehicle.vehicle_id} \
            --endpoint-url "{vehicle.endpoint_address}" \
            --topic-prefix '$aws/iotfleetwise/' \
            --can-bus0 "vcan0"

            # Install source deps
            ./tools/install-deps-native.sh

            # Build source
            sudo -u ubuntu ./tools/build-fwe-native.sh

            # Install FWE
            ./tools/install-fwe.sh

            # Signal init complete:
            /opt/aws/bin/cfn-signal --stack {Aws.STACK_NAME} \
                --resource {instance.instance.logical_id} --region {Aws.REGION}'''

        instance.add_user_data(user_data)
        CfnOutput(self, 'Vehicle IP Address',
                  value=instance.instance_public_ip)
        CfnOutput(self, 'Vehicle ssh command',
                  value=f'ssh -i {key_name}.pem ubuntu@{instance.instance_public_ip}')
