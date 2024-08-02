#!/usr/bin/env python3
import sys

import aws_cdk as cdk
import utils
from local_tax_mgmt.stack import LocalTaxMgmtStack


app = cdk.App()

# Get target stage from cdk context
stage = app.node.try_get_context("stage")
if stage is None or stage == "unknown":
    sys.exit(
        "Missing stage context variable. USAGE: cdk <command> -c stage=dev"
    )

stage_config = utils.load_stage_config(stage=stage)

LocalTaxMgmtStack(scope=app, id="LocalTaxMgmtStack", config=stage_config)

app.synth()
