from aws_cdk import Stack, aws_ec2 as ec2
from constructs import Construct
from .s3 import S3Construct
from .aurora import AuroraConstruct


class LocalTaxMgmtStack(Stack):

    def __init__(
        self, scope: Construct, id: str, config: dict, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        vpc = ec2.Vpc.from_lookup(
            scope=self,
            id="VPC",
            vpc_id=config["vpc_id"],
        )

        aurora = AuroraConstruct(
            scope=self, id="AuroraConstruct", config=config, vpc=vpc
        )

        s3 = S3Construct(scope=self, id="S3Construct", config=config)
