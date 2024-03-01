#!/usr/bin/env python3

import aws_cdk as cdk
from cdk.cdk_stack import CdkStack

app = cdk.App()
env = cdk.Environment(
    account="xxxxxxxxxxxx",
    region="us-east-1",
)
CdkStack(app, "cdk", env=env)

app.synth()
