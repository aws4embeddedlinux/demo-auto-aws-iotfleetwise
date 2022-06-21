from aws_cdk import (
  Stack,
  CfnOutput,
  Duration,
  Aws,
  aws_codecommit as cc,
  aws_codebuild as cb,
  aws_codepipeline as cp,
  aws_codepipeline_actions as cpa,
  aws_iam as iam
)
from constructs import Construct


class AglPipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # CodeBuild Role
        role = iam.Role(self, "BuildRole", 
                        assumed_by=iam.ServicePrincipal(
                            "codebuild.amazonaws.com"),
                        managed_policies=[
                            iam.ManagedPolicy.from_aws_managed_policy_name(
                                "AWSCodeCommitPowerUser"),
                            iam.ManagedPolicy.from_aws_managed_policy_name(
                                "AWSIoTFullAccess")])
        repository = cc.Repository(self, "Repo",
                                   repository_name='demo-auto-aws-iot-fleetwise-agl',
                                   code=cc.Code.from_directory(
                                       'src/repo-agl-seed/',
                                       'main'))

        # Creating the pipeline
        project = cb.PipelineProject(self, "Project",
                                     role=role,
                                     environment=cb.BuildEnvironment(
                                        compute_type=cb.ComputeType.LARGE,
                                        build_image=cb.LinuxBuildImage.STANDARD_5_0),
                                     environment_variables={
                                         "AWS_ACCOUNT_ID": cb.BuildEnvironmentVariable(
                                             value=Aws.ACCOUNT_ID),
                                         "AWS_REGION": cb.BuildEnvironmentVariable(
                                             value=Aws.REGION)},
                                     timeout=Duration.hours(6))
   
        source_artifact = cp.Artifact()
        source_action = cpa.CodeCommitSourceAction(
                action_name="CodeCommitSource",
                repository=repository,
                output=source_artifact,
                branch='main'
        )
        build_action = cpa.CodeBuildAction(
                action_name="build_image",
                project=project,
                input=source_artifact
        )
        pipeline = cp.Pipeline(self, "Pipeline",
                               stages=[
                                   cp.StageProps(stage_name="Source",
                                                 actions=[source_action]),
                                   cp.StageProps(stage_name="Build",
                                                 actions=[build_action])])

        CfnOutput(self, "PipelineOut",
                  description="Pipeline",
                  value=pipeline.pipeline_name)
