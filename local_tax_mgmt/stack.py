from aws_cdk import Stack
from constructs import Construct

from .s3 import S3Construct


class LocalTaxMgmtStack(Stack):

    def __init__(
        self, scope: Construct, id: str, config: dict, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        s3 = S3Construct(scope=self, id="S3Construct", config=config)
