#!/usr/bin/env python3
import os
import aws_cdk as cdk
from src.main_stack import MainStack
from src.agl_stack import AglPipelineStack


app = cdk.App()
MainStack(app, "demo-auto-aws-iotfleetwise",
          env=cdk.Environment(
            account=os.getenv('CDK_DEFAULT_ACCOUNT'),
            region=os.getenv('CDK_DEFAULT_REGION')))

AglPipelineStack(app, "demo-auto-aws-iotfleetwise-agl-pipeline",
                 env=cdk.Environment(
                   account=os.getenv('CDK_DEFAULT_ACCOUNT'),
                   region=os.getenv('CDK_DEFAULT_REGION')))

app.synth()
