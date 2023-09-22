import os

from aws_cdk import (
    Stack,
    DockerImage,
    BundlingOptions,
    aws_s3 as s3,
    aws_s3_assets as assets,
    aws_iam as iam,
    aws_codepipeline as codepipeline,
    aws_codebuild as codebuild,
    aws_codepipeline_actions as pipeline_actions,
    aws_codecommit as codecommit,
)
from constructs import Construct


class FweGgv2PipelineStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # CodeCommit repository is created for component listed here example for
        repository_name = 'fwe-ggv2-component'
        branch = 'main'

        # Workaround for https://github.com/aws/aws-cdk/issues/19012        
        repo_asset = assets.Asset(
            self, "RepositoryCodeAsset",
            path=os.path.join('./greengrass_components/', 'repo-fwe-ggv2-seed'),
            bundling=BundlingOptions(
                image=DockerImage.from_registry(
                    image="public.ecr.aws/docker/library/alpine:latest"
                ),
                command=[
                    "sh",
                    "-c",
                    """
                        apk update && apk add zip
                        cd asset-input
                        zip -r /asset-output/code.zip .
                        """,
                ],
                user="root",
            ))
        
        repository = codecommit.Repository(
            self, "Repository",
            repository_name=repository_name,
            code=codecommit.Code.from_asset(
                asset = repo_asset,
                branch=branch
            ))

        pipeline = codepipeline.Pipeline(self, "Pipeline")

        # add a stage
        source_stage = pipeline.add_stage(stage_name="Source")

        # add a source action to the stage
        source_stage.add_action(pipeline_actions.CodeCommitSourceAction(
            action_name="Source",
            output=codepipeline.Artifact(artifact_name="SourceArtifact"),
            repository=repository,
            branch=branch))

        project = codebuild.Project(self, "Project",
                                    build_spec=codebuild.BuildSpec.from_source_filename(
                                        'buildspec.yml'),
                                    source=codebuild.Source.code_commit(
                                        repository=repository),
                                    environment=codebuild.BuildEnvironment(
                                        build_image=codebuild.LinuxBuildImage.from_code_build_image_id('aws/codebuild/standard:4.0')),
                                    environment_variables={
                                        "COMPONENT_NAME": codebuild.BuildEnvironmentVariable(
                                            value=repository_name),
                                        "COMPONENT_DIRECTORY": codebuild.BuildEnvironmentVariable(
                                            value='.'),
                                        "S3_PATH": codebuild.BuildEnvironmentVariable(
                                            value=f's3://{pipeline.artifact_bucket.bucket_name}/components')})

        project.role.add_to_policy(iam.PolicyStatement(
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
            ]))

        # add a stage
        build_stage = pipeline.add_stage(stage_name="Build")

        # add a source action to the stage
        build_stage.add_action(pipeline_actions.CodeBuildAction(
            action_name="Build",
            input=codepipeline.Artifact(artifact_name="SourceArtifact"),
            project=project))