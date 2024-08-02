from constructs import Construct
from aws_cdk import aws_s3 as s3

from utils import normalize_resource_name


class S3Construct(Construct):
    def __init__(self, scope: Construct, id: str, config: dict) -> None:
        super().__init__(scope, id)
        self._buckets = {}

        for bucket_config in config["s3"]:
            bucket_name = bucket_config["bucket_name"]
            self._buckets[bucket_name] = s3.Bucket(
                scope=self,
                id=normalize_resource_name(bucket_name),
                **bucket_config
            )

    @property
    def buckets(self):
        return self._buckets
