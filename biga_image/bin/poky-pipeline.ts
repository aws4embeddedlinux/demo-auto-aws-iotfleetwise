#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import {
  DemoPipelineStack,
  BuildImageDataStack,
  BuildImagePipelineStack,
  BuildImageRepoStack,
  PipelineNetworkStack,
  ImageKind,
  ProjectKind,
} from "aws4embeddedlinux-cdk-lib";
import * as path from 'path';

const app = new cdk.App();

/* See https://docs.aws.amazon.com/sdkref/latest/guide/access.html for details on how to access AWS. */
const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION,
};

/**
 * Use these default props to enable termination protection and tag related AWS
 * Resources for tracking purposes.
 */
const defaultProps: cdk.StackProps = {
  tags: { PURPOSE: "META-AWS-BUILD" },
  terminationProtection: false, // TODO: enable or remove.
  env,
};

/**
 * Set up the Stacks that create our Build Host.
 */
const buildImageData = new BuildImageDataStack(app, "BuildImageData", {
  ...defaultProps,
  bucketName: `build-image-data-${env.account}-${env.region}`,
});

const buildImageRepo = new BuildImageRepoStack(app, "BuildImageRepo", {
  ...defaultProps,
});

new BuildImagePipelineStack(app, "BuildImagePipeline", {
  ...defaultProps,
  dataBucket: buildImageData.bucket,
  repository: buildImageRepo.repository,
  imageKind: ImageKind.Ubuntu22_04,
});

/**
 * Set up networking to allow us to securely attach EFS to our CodeBuild instances.
 */
const vpc = new PipelineNetworkStack(app, {
  ...defaultProps,
});


/**
 * Create a biga pipeline for agl-nxp-goldbox.
 */
new DemoPipelineStack(app, "AglNxpGoldboxBigaPipeline", {
  ...defaultProps,
  imageRepo: buildImageRepo.repository,
  imageTag: ImageKind.Ubuntu22_04,
  vpc: vpc.vpc,
  layerRepoName: "agl-nxp-goldbox-biga-layer-repo",
  projectKind: ProjectKind.MetaAwsDemo,
});
