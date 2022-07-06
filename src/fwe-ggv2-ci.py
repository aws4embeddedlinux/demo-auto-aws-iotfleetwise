import os

from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_s3_assets as asset,
    aws_iam as iam,
    aws_codepipeline as codepipeline,
    aws_codebuild as codebuild,
    aws_codepipeline_actions as pipeline_actions,
    aws_codecommit as codecommit,
)
from constructs import Construct


class Ggv2CicdCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Token exchange role name used by Greengrass (specified during GG setup)
        token_exchange_role_name = "role/GreengrassV2TokenExchangeRole"

        # Greengrass role (change the role name if you need)
        greengrass_token_exchange_role = iam.Role.from_role_arn(
            self, 'greengrassRole',
            "arn:aws:iam::{}:{}".format(self.account, token_exchange_role_name),
            mutable=True
        )

        # Allow greengrass to use AWS Cloudwatch logs.
        greengrass_token_exchange_role.add_to_principal_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=['*'],
            sid="CloudwatchGGv2Component",
            actions=[
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogStreams"
            ])
        )

        # CodeCommit repository is created for component listed here example for
        ggv2_component = 'fleetwise-edge-agent-ggv2-component'

        fwe_ggv2_component_asset = asset.Asset(self, 'GGv2ComponentAsset', path=os.path.join('.', 'fwe-ggv2-component'))
        
        components_bucket = s3.Bucket(self, 'GGv2ComponentsBucket')

        repo = codecommit.Repository(
            self, str(ggv2_component),
            repository_name=str(ggv2_component),
            code=codecommit.Code.from_asset(
                asset=fwe_ggv2_component_asset,
                branch="dev"
            )
        )

        # dev pipeline
        branch_name = 'dev',

        repo_object = codecommit.Repository.from_repository_arn(self,
                                                                f'repo_arn-{ggv2_component}',
                                                                repository_arn=repo.repository_arn)

        component_pipeline = codepipeline.Pipeline(self, f'{ggv2_component}-pipeline')

        # add a stage
        source_stage = component_pipeline.add_stage(stage_name="Source")

        # add a source action to the stage
        source_stage.add_action(pipeline_actions.CodeCommitSourceAction(
            action_name="Source",
            output=codepipeline.Artifact(artifact_name="SourceArtifact"),
            repository=repo_object,
            branch=branch_name
        ))

        ggv2_component_build_project = codebuild.Project(self, f'build-{ggv2_component}',
                                                         build_spec=codebuild.BuildSpec.from_source_filename(
                                                             'buildspec.yml'),
                                                         source=codebuild.Source.code_commit(
                                                             repository=repo_object),
                                                         environment=codebuild.BuildEnvironment(
                                                             build_image=codebuild.LinuxBuildImage.from_code_build_image_id('aws/codebuild/standard:5.0')),
                                                         environment_variables={
                                                             "COMPONENT_NAME": codebuild.BuildEnvironmentVariable(
                                                                 value=ggv2_component),
                                                             "COMPONENT_DIRECTORY": codebuild.BuildEnvironmentVariable(
                                                                 value='.'),
                                                             "S3_PATH": codebuild.BuildEnvironmentVariable(
                                                                 value=f's3://{components_bucket.bucket_name}/components')
                                                         })

        ggv2_component_build_project.role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=['*'],
            actions=[
                'greengrass:CreateComponentVersion',
                'greengrass:ListComponentVersions',
                'greengrass:CreateDeployment',
                'iot:DescribeThing',
                'iot:UpdateThingShadow',
                'iot:DescribeThingGroup',
                'iot:DescribeJob',
                'iot:CreateJob',
                'iot:CancelJob'
            ]
        ))

        ggv2_component_build_project.role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[f'{components_bucket.bucket_arn}/components/{ggv2_component}/*'],
            actions=[
                's3:*',
            ]
        ))

        # add a stage
        build_stage = component_pipeline.add_stage(stage_name="Build")

        # add a source action to the stage
        build_stage.add_action(pipeline_actions.CodeBuildAction(
            action_name=f"Build-{branch_name}",
            input=codepipeline.Artifact(artifact_name="SourceArtifact"),
            project=ggv2_component_build_project
        ))