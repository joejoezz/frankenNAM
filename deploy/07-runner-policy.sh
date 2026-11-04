#!/usr/bin/env bash
# Let a runner launch the next runner (self-chaining, approved by Joe 4 Nov 2026): an inline policy
# on the nam-recast-ec2 role with RunInstances/CreateTags scoped to project=nam-recast tags,
# TerminateInstances scoped to that resource tag, the Describe calls launch.sh needs, PassRole for
# the role itself (to EC2 only) and GetParameter for the public Canonical AMI parameter.
# Idempotent: put-role-policy replaces the policy of the same name.
set -euo pipefail
export AWS_DEFAULT_REGION=${AWS_REGION:-us-west-2}
ROLE=nam-recast-ec2
ACCOUNT=617711905691
REGION=$AWS_DEFAULT_REGION
POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RunTaggedInstances",
      "Effect": "Allow",
      "Action": "ec2:RunInstances",
      "Resource": ["arn:aws:ec2:$REGION:$ACCOUNT:instance/*", "arn:aws:ec2:$REGION:$ACCOUNT:volume/*"],
      "Condition": {"StringEquals": {"aws:RequestTag/project": "nam-recast"}}
    },
    {
      "Sid": "RunInstancesSupportingResources",
      "Effect": "Allow",
      "Action": "ec2:RunInstances",
      "Resource": [
        "arn:aws:ec2:$REGION::image/ami-*",
        "arn:aws:ec2:$REGION:$ACCOUNT:subnet/*",
        "arn:aws:ec2:$REGION:$ACCOUNT:security-group/*",
        "arn:aws:ec2:$REGION:$ACCOUNT:network-interface/*",
        "arn:aws:ec2:$REGION:$ACCOUNT:key-pair/nam-recast"
      ]
    },
    {
      "Sid": "TagAtLaunch",
      "Effect": "Allow",
      "Action": "ec2:CreateTags",
      "Resource": "arn:aws:ec2:$REGION:$ACCOUNT:*/*",
      "Condition": {"StringEquals": {"ec2:CreateAction": "RunInstances"}}
    },
    {
      "Sid": "Describe",
      "Effect": "Allow",
      "Action": ["ec2:DescribeInstances", "ec2:DescribeImages", "ec2:DescribeSubnets", "ec2:DescribeSecurityGroups",
                 "ec2:DescribeInstanceStatus", "ec2:DescribeSpotInstanceRequests", "ec2:DescribeSpotPriceHistory"],
      "Resource": "*"
    },
    {
      "Sid": "TerminateProjectInstances",
      "Effect": "Allow",
      "Action": "ec2:TerminateInstances",
      "Resource": "arn:aws:ec2:$REGION:$ACCOUNT:instance/*",
      "Condition": {"StringEquals": {"aws:ResourceTag/project": "nam-recast"}}
    },
    {
      "Sid": "PassOwnRoleToEC2",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::$ACCOUNT:role/$ROLE",
      "Condition": {"StringEquals": {"iam:PassedToService": "ec2.amazonaws.com"}}
    },
    {
      "Sid": "CanonicalAmiParameter",
      "Effect": "Allow",
      "Action": "ssm:GetParameter",
      "Resource": "arn:aws:ssm:$REGION::parameter/aws/service/canonical/*"
    }
  ]
}
EOF
)
aws iam put-role-policy --role-name $ROLE --policy-name nam-recast-chain --policy-document "$POLICY"
echo "policy nam-recast-chain on role $ROLE:"
aws iam get-role-policy --role-name $ROLE --policy-name nam-recast-chain --query 'PolicyDocument.Statement[].Sid' --output text
