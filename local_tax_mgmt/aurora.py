from constructs import Construct
from aws_cdk import RemovalPolicy
from aws_cdk.aws_ec2 import (
    IVpc,
    Instance,
    InstanceType,
    MachineImage,
    BlockDevice,
    BlockDeviceVolume,
    SubnetSelection,
    SubnetType,
    SecurityGroup,
    Port,
    Protocol,
    Peer,
)
from aws_cdk.aws_rds import (
    DatabaseCluster,
    DatabaseClusterEngine,
    AuroraMysqlEngineVersion,
    Credentials,
    CaCertificate,
    ParameterGroup,
    ClusterInstance,
)
from aws_cdk.aws_iam import (
    ManagedPolicy,
    ServicePrincipal,
    PolicyDocument,
    PolicyStatement,
    Effect,
    Role,
)
from utils import normalize_resource_name


class AuroraConstruct(Construct):

    def __init__(
        self, scope: Construct, id: str, config: dict, vpc: IVpc
    ) -> None:
        super().__init__(scope, id)
        aurora_config = config["aurora"]

        removal_policy = RemovalPolicy[aurora_config["removal_policy"]]
        engine = DatabaseClusterEngine.aurora_mysql(
            version=AuroraMysqlEngineVersion.VER_3_07_0
        )
        self.db_port = aurora_config["database_port"]

        # Create Aurora Serverless V2 Cluster
        self.aurora_cluster = DatabaseCluster(
            scope=self,
            id=normalize_resource_name(aurora_config["cluster_id"]),
            cluster_identifier=aurora_config["cluster_id"],
            parameter_group=ParameterGroup(
                scope=self,
                id="TimezoneParameterGroup",
                engine=engine,
                parameters={"time_zone": "Europe/Rome"},
            ),
            engine=engine,
            copy_tags_to_snapshot=True,
            credentials=Credentials.from_generated_secret(
                username=aurora_config["username"],
                secret_name=aurora_config["credentials_secret_name"],
            ),
            default_database_name=aurora_config["database_name"],
            port=self.db_port,
            storage_encrypted=True,
            removal_policy=removal_policy,
            vpc=vpc,
            vpc_subnets=SubnetSelection(
                subnet_type=SubnetType.PRIVATE_WITH_EGRESS
            ),
            writer=ClusterInstance.serverless_v2(
                id="ServerlessWriter",
                auto_minor_version_upgrade=False,
                ca_certificate=CaCertificate.RDS_CA_RDS2048_G1,
                instance_identifier=aurora_config["writer_instance_id"],
            ),
            serverless_v2_min_capacity=aurora_config["min_capacity"],
            serverless_v2_max_capacity=aurora_config["max_capacity"],
            deletion_protection=removal_policy != RemovalPolicy.DESTROY,
        )

        # Create RDS Proxy
        rds_proxy_config = aurora_config["rds_proxy"]
        self.rds_proxy_role = Role(
            scope=self,
            id=normalize_resource_name(rds_proxy_config["role_name"]),
            role_name=rds_proxy_config["role_name"],
            assumed_by=ServicePrincipal(service="rds.amazonaws.com"),  # type: ignore
            inline_policies={
                "ssm_secret_access": PolicyDocument(
                    statements=[
                        PolicyStatement(
                            actions=["secretsmanager:GetSecretValue"],
                            effect=Effect.ALLOW,
                            resources=[self.aurora_cluster.secret.secret_arn],  # type: ignore
                        )
                    ]
                )
            },
        )
        # Define security group for rds proxy
        self.rds_proxy_security_group = SecurityGroup(
            scope=self,
            id=normalize_resource_name(rds_proxy_config["security_group"]),
            security_group_name=rds_proxy_config["security_group"],
            vpc=vpc,
            allow_all_outbound=True,
        )

        self.rds_proxy = self.aurora_cluster.add_proxy(
            id=normalize_resource_name(rds_proxy_config["name"]),
            db_proxy_name=rds_proxy_config["name"],
            vpc=vpc,
            vpc_subnets=SubnetSelection(
                subnet_type=SubnetType.PRIVATE_WITH_EGRESS
            ),
            role=self.rds_proxy_role,  # type: ignore
            security_groups=[self.rds_proxy_security_group],
            secrets=[self.aurora_cluster.secret],  # type: ignore
            iam_auth=True,
        )

        self.proxy_access_policy = ManagedPolicy(
            scope=self,
            id="RdsProxyAccessPolicy",
            managed_policy_name="-access-to-proxy-policy",
            description="Policy to grant access to RDS Proxy",
            document=PolicyDocument(
                statements=[
                    PolicyStatement(
                        actions=["rds-db:connect"],
                        effect=Effect.ALLOW,
                        resources=[
                            f"arn:aws:rds-db:*:*:dbuser:*/*",
                        ],
                    ),
                ]
            ),
        )

        bh_config = aurora_config["bastion_host"]

        if bh_config["enabled"]:
            self.bh_security_group = SecurityGroup(
                scope=self,
                id=normalize_resource_name(bh_config["security_group"]),
                security_group_name=bh_config["security_group"],
                allow_all_outbound=True,
                vpc=vpc,
            )
            self.bh_instance = Instance(
                scope=self,
                id=normalize_resource_name(bh_config["name"]),
                instance_name=bh_config["name"],
                instance_type=InstanceType("t3.micro"),
                security_group=self.bh_security_group,
                machine_image=MachineImage.latest_amazon_linux2(),
                vpc=vpc,
                vpc_subnets=SubnetSelection(subnets=vpc.private_subnets),
                user_data_causes_replacement=True,
                block_devices=[
                    BlockDevice(
                        device_name="/dev/xvda",
                        volume=BlockDeviceVolume.ebs(
                            volume_size=30, encrypted=True
                        ),
                    )
                ],
                ssm_session_permissions=True,
                propagate_tags_to_volume_on_creation=True,
            )

            # Ingress rule for Bastion Host
            self.aurora_cluster._security_groups[0].add_ingress_rule(
                connection=Port(
                    protocol=Protocol.TCP,  # type: ignore
                    from_port=self.db_port,
                    to_port=self.db_port,
                    string_representation="Custom TCP",
                ),
                description="Rule to enable bh communication",
                peer=Peer.security_group_id(
                    self.bh_security_group.security_group_id
                ),
            )

    def grant_proxy_connection(self, security_group_id: str):
        self.rds_proxy_security_group.add_ingress_rule(
            connection=Port(
                protocol=Protocol.TCP,  # type: ignore
                from_port=self.db_port,
                to_port=self.db_port,
                string_representation="Custom TCP",
            ),
            description=f"Rule to enable communication from sg {security_group_id}",
            peer=Peer.security_group_id(security_group_id),
        )
