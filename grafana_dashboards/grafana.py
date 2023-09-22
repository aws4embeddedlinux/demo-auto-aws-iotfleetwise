from aws_cdk import (
    CfnOutput,
    Aws,
    RemovalPolicy,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_efs as efs,
    aws_logs as logs,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    aws_ecs_patterns as ecs_patterns,
    aws_ecr_assets as ecr_assets
)
from constructs import Construct


class Grafana(Construct):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        vpc = ec2.Vpc.from_lookup(self, 'VPC', is_default=True)

        cluster = ecs.Cluster(self, "MyCluster", vpc=vpc)

        file_system = efs.FileSystem(self, 'EfsFileSystem',
                                     vpc=vpc,
                                     encrypted=True,
                                     lifecycle_policy=efs.LifecyclePolicy.AFTER_14_DAYS,
                                     performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
                                     throughput_mode=efs.ThroughputMode.BURSTING,
                                     # WARNING: This shouldn't be used in production
                                     removal_policy=RemovalPolicy.DESTROY)

        access_point = efs.AccessPoint(self, 'EfsAccessPoint',
                                       file_system=file_system,
                                       path='/var/lib/grafana',
                                       posix_user={
                                           'gid': '1000',
                                           'uid': '1000'
                                       },
                                       create_acl={
                                           'owner_gid': '1000',
                                           'owner_uid': '1000',
                                           'permissions': '755'
                                       })

        # task log group
        log_group = logs.LogGroup(self, 'taskLogGroup',
                                  retention=logs.RetentionDays.ONE_MONTH)

        # container log driver
        container_log_driver = ecs.LogDrivers.aws_logs(
            stream_prefix=Aws.STACK_NAME,
            log_group=log_group)

        # task Role
        task_role = iam.Role(self, 'taskRole',
                             assumed_by=iam.ServicePrincipal('ecs-tasks.amazonaws.com'))

        task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    'timestream:*'
                ],
                resources=['*']))

        # execution Role
        execution_role = iam.Role(self, 'executionRole',
                                  assumed_by=iam.ServicePrincipal('ecs-tasks.amazonaws.com'))

        execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    'logs:CreateLogStream',
                    'logs:PutLogEvents',
                ],
                resources=[
                    log_group.log_group_arn
                ]))

        # Create Task Definition
        volume_name = 'efsGrafanaVolume'

        volume_config = {
            'name': volume_name,
            'efsVolumeConfiguration': {
                'fileSystemId': file_system.file_system_id,
                'transitEncryption': 'ENABLED',
                'authorizationConfig': {'accessPointId': access_point.access_point_id}
            }}

        task_definition = ecs.FargateTaskDefinition(self, "TaskDef",
                                                    task_role=task_role,
                                                    execution_role=execution_role,
                                                    volumes=[volume_config])

        # Grafana Admin Password
        grafanaAdminPassword = secretsmanager.Secret(self, 'grafanaAdminPassword')
        # Allow Task to access Grafana Admin Password
        grafanaAdminPassword.grant_read(task_role)

        # Our Grafana image
        image = ecr_assets.DockerImageAsset(self, "GrafanaImage",
                                            directory='grafana_dashboards/grafana-image')
        # Web Container
        container_web = task_definition.add_container(
            "web",
            image=ecs.ContainerImage.from_docker_image_asset(image),  
            logging=container_log_driver,
            secrets={
                'GF_SECURITY_ADMIN_PASSWORD':
                    ecs.Secret.from_secrets_manager(grafanaAdminPassword)
            })

        # set port mapping
        container_web.add_port_mappings(ecs.PortMapping(container_port=3000))

        container_web.add_mount_points(ecs.MountPoint(
            source_volume=volume_config['name'],
            container_path='/var/lib/grafana',
            read_only=False))

        # Create a load-balanced Fargate service and make it public
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "MyFargateService",
            cluster=cluster,
            cpu=1024,
            desired_count=1,
            task_definition=task_definition,
            memory_limit_mib=2048,
            protocol=elbv2.ApplicationProtocol.HTTP,
            platform_version=ecs.FargatePlatformVersion.VERSION1_4,
            assign_public_ip=True)

        fargate_service.task_definition.find_container("web").add_environment(
            "GF_SERVER_ROOT_URL",
            f"http://{fargate_service.load_balancer.load_balancer_dns_name}")
        fargate_service.target_group.configure_health_check(
          path='/api/health')

        # Allow Task to access EFS
        file_system.connections.allow_default_port_from(
            fargate_service.service.connections)

        aws_get_secret = "aws secretsmanager get-secret-value --secret-id"
        CfnOutput(self, "GrafanaAdminPassword",
                  value=f"{aws_get_secret} {grafanaAdminPassword.secret_name}|jq .SecretString -r")
