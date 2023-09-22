#!/usr/bin/env python3
import os
import aws_cdk as cdk
from iot_fleetwise_setup.main_stack import MainStack
from iot_data_ingestion_pipeline.visibility_stack import VisibilityStack

app = cdk.App()
MainStack(app, "biga-aws-iotfleetwise",
          env=cdk.Environment(
            account=os.getenv('CDK_DEFAULT_ACCOUNT'),
            region=os.getenv('CDK_DEFAULT_REGION')))

VisibilityStack(app, "VisibilityStack",

                env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION'))
                )
app.synth()
