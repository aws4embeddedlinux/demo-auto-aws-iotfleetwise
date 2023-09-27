# Meta-AWS CDK Library

An AWS [Cloud Developer Toolkit](https://docs.aws.amazon.com/cdk/v2/guide/home.html) Library for building Yocto projects in AWS.

## Quickstart
to create yocto demo build pipelines and cloud resources.

### Setting Up

#### install npm packages:

```bash
npm install .
```

#### updating - if you have an already have packages installed before
```bash
npm update
```

#### build:

```bash
npm run build
```

#### deploy cloud resources for all demo pipelines:
```bash
# only required once
cdk bootstrap

cdk deploy --all
```

The newly created pipeline `ubuntu_22_04BuildImagePipeline` from the CodePipeline console will start automatically.

After that completes, the DemoPipeline in the CodePipeline console page is ready to run.

#### seed repo with biga buildspec:
```bash
aws codecommit put-file \
    --repository-name agl-nxp-goldbox-biga-layer-repo \
    --branch-name main \
    --file-content file://repo_seed/build.buildspec.yml \
    --file-path /build.buildspec.yml \
    --parent-commit-id $(aws codecommit get-branch --repository-name agl-nxp-goldbox-biga-layer-repo --branch-name main --query 'branch.commitId' --output text) \
    --commit-message "commit repo_seed" \
    --cli-binary-format raw-in-base64-out
```


#### destroy cloud resources for all demo pipelines:
```bash
cdk destroy --all
```

## Useful commands

-   `npm run build` compile typescript to js
-   `npm run watch` watch for changes and compile
-   `npm run test` perform the jest unit tests
-   `cdk deploy` deploy this stack to your default AWS account/region
-   `cdk diff` compare deployed stack with current state
-   `cdk synth` emits the synthesized CloudFormation template

Project Specific:
-   `npm run format` runs prettier and eslint on the repository
-   `npm run zip-data` bundles the files for creating build host containers
-   `npm run check` checks for lint and format issues
-   `npm run docs` to generate documentation

## Contributing

TODO: Notes contribution process (pre-commit, running tests, formatting and test standards, etc)
