"""An AWS Python Pulumi program"""

import pulumi
import pulumi_aws as aws

ami = aws.get_ami(
    most_recent=True,
    owners=["137112412989"],
    filters=[{"name": "name", "values": ["amzn-ami-hvm-*-x86_64-ebs"]}],
)

vpc = aws.ec2.get_vpc(default=True)
vpc_subnets = aws.ec2.get_subnet_ids(vpc_id=vpc.id)

group = aws.ec2.SecurityGroup(
    "web-secgrp",
    description="Enable HTTP Access",
    vpc_id=vpc.id,
    ingress=[
        {
            "protocol": "icmp",
            "from_port": 8,
            "to_port": 0,
            "cidr_blocks": ["0.0.0.0/0"],
        },
        {
            "protocol": "tcp",
            "from_port": 80,
            "to_port": 80,
            "cidr_blocks": ["0.0.0.0/0"],
        },
    ],
    egress=[
        {
            "protocol": "tcp",
            "from_port": 80,
            "to_port": 80,
            "cidr_blocks": ["0.0.0.0/0"],
        }
    ],
)

lb = aws.lb.LoadBalancer(
    "loadbalancer",
    internal=False,
    security_groups=[group.id],
    subnets=vpc_subnets.ids,
    load_balancer_type="application",
)

target_groups = [
    aws.lb.TargetGroup("target-group1", port=80, protocol="HTTP", target_type="ip", vpc_id=vpc.id),
    aws.lb.TargetGroup("target-group2", port=80, protocol="HTTP", target_type="ip", vpc_id=vpc.id),
]

ips = []
hostnames = []

listener = aws.lb.Listener(
    "listener",
    load_balancer_arn=lb.arn,
    port=80,
    default_actions=[{"type": "forward", "target_group_arn": target_groups[0].arn}],
)

for i in [1, 2]:
    listener_rule = aws.lb.ListenerRule(f"static{i}",
        listener_arn=listener.arn,
        priority=i,
        actions=[aws.lb.ListenerRuleActionArgs(
            type="forward",
            target_group_arn=target_groups[i - 1].arn,
        )],
        conditions=[aws.lb.ListenerRuleConditionArgs(
            path_pattern=aws.lb.ListenerRuleConditionPathPatternArgs(
               values=[f"/{i}"],
            ),
        ),
    ])

    if i == 1:
        server = aws.ec2.Instance(
            f"web-server-{i}",
            instance_type="t2.micro",
            vpc_security_group_ids=[group.id],
            ami=ami.id,
            user_data="""#!/bin/bash
            echo \"Hello, World -- from 1!\" > index.html
            nohup python -m SimpleHTTPServer 80 &
            """,
            tags={
                "Name": "web-server",
            },
        )
    else:
        server = aws.ec2.Instance(
            f"web-server-{i}",
            instance_type="t2.micro",
            vpc_security_group_ids=[group.id],
            ami=ami.id,
            user_data="""#!/bin/bash
            mkdir 2
            cd 2
            echo \"Hello, World -- from dir 2!\" > index.html
            cd ..
            echo \"Hello, World -- from 2!\" > index.html
            nohup python -m SimpleHTTPServer 80 &
            """,
            tags={
                "Name": "web-server",
            },
        )

    ips.append(server.public_ip)
    hostnames.append(server.public_dns)

    attachment = aws.lb.TargetGroupAttachment(
        f"web-server-{i}",
        target_group_arn=target_groups[i - 1].arn,
        target_id=server.private_ip,
        port=80,
    )

pulumi.export("ips", ips)
pulumi.export("hostnames", hostnames)
pulumi.export("url", lb.dns_name)
