from aws_cdk import Stack
from constructs import Construct


class LocalTaxMgmtStack(Stack):

    def __init__(
        self, scope: Construct, id: str, config: dict, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)
