---
name: aws-cdk-development
description: Build AWS infrastructure using CDK (Cloud Development Kit). Use when the user asks to create AWS infrastructure, deploy cloud resources, write CDK stacks, or manage AWS services with infrastructure as code.
metadata:
  author: zxkane
  version: "1.0.0"
---

# AWS CDK Development

Help users build and deploy AWS infrastructure using the AWS Cloud Development Kit (CDK).

## Prerequisites

### Installation
```bash
npm install -g aws-cdk
```

### Project Initialization
```bash
# TypeScript (recommended)
cdk init app --language typescript

# Python
cdk init app --language python
```

## CDK Project Structure

```
my-cdk-app/
├── bin/
│   └── app.ts              # App entry point
├── lib/
│   └── my-stack.ts         # Stack definitions
├── test/
│   └── my-stack.test.ts    # Stack tests
├── cdk.json                # CDK configuration
├── package.json
└── tsconfig.json
```

## Core Concepts

### Stack Definition
```typescript
import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as lambda from "aws-cdk-lib/aws-lambda";

export class MyStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const bucket = new s3.Bucket(this, "DataBucket", {
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    const fn = new lambda.Function(this, "Handler", {
      runtime: lambda.Runtime.NODEJS_20_X,
      handler: "index.handler",
      code: lambda.Code.fromAsset("lambda"),
      environment: {
        BUCKET_NAME: bucket.bucketName,
      },
    });

    bucket.grantRead(fn);
  }
}
```

### App Entry Point
```typescript
import * as cdk from "aws-cdk-lib";
import { MyStack } from "../lib/my-stack";

const app = new cdk.App();
new MyStack(app, "MyStack", {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});
```

## Common Patterns

### API Gateway + Lambda
```typescript
import * as apigateway from "aws-cdk-lib/aws-apigateway";

const api = new apigateway.RestApi(this, "Api", {
  restApiName: "My Service",
});

const items = api.root.addResource("items");
items.addMethod("GET", new apigateway.LambdaIntegration(fn));
items.addMethod("POST", new apigateway.LambdaIntegration(fn));
```

### DynamoDB Table
```typescript
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";

const table = new dynamodb.Table(this, "Table", {
  partitionKey: { name: "pk", type: dynamodb.AttributeType.STRING },
  sortKey: { name: "sk", type: dynamodb.AttributeType.STRING },
  billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
  removalPolicy: cdk.RemovalPolicy.RETAIN,
});
```

### SQS Queue with Dead Letter Queue
```typescript
import * as sqs from "aws-cdk-lib/aws-sqs";

const dlq = new sqs.Queue(this, "DeadLetterQueue", {
  retentionPeriod: cdk.Duration.days(14),
});

const queue = new sqs.Queue(this, "Queue", {
  visibilityTimeout: cdk.Duration.seconds(300),
  deadLetterQueue: {
    queue: dlq,
    maxReceiveCount: 3,
  },
});
```

## CDK Commands

```bash
# Synthesize CloudFormation template
cdk synth

# Compare deployed stack with current state
cdk diff

# Deploy stack
cdk deploy

# Deploy with auto-approve
cdk deploy --require-approval never

# Destroy stack
cdk destroy

# List stacks
cdk ls
```

## Best Practices

1. **Use L2 constructs** — Prefer high-level constructs over L1 (Cfn*) constructs
2. **Enable removal policies** — Set explicit removal policies for stateful resources
3. **Use environment variables** — Pass configuration via CDK context or environment variables
4. **Write snapshot tests** — Test infrastructure with `cdk.assertions`
5. **Tag resources** — Apply consistent tags for cost tracking and organization
6. **Use aspects** — Apply cross-cutting concerns like tagging via CDK Aspects
7. **Separate stacks** — Group related resources; separate stateful from stateless
8. **Pin construct versions** — Lock dependency versions for reproducible deployments

## Testing

```typescript
import * as cdk from "aws-cdk-lib";
import { Template } from "aws-cdk-lib/assertions";
import { MyStack } from "../lib/my-stack";

test("S3 bucket created with versioning", () => {
  const app = new cdk.App();
  const stack = new MyStack(app, "TestStack");
  const template = Template.fromStack(stack);

  template.hasResourceProperties("AWS::S3::Bucket", {
    VersioningConfiguration: { Status: "Enabled" },
  });
});
```

## Security Guidelines

- Never hardcode credentials or secrets in CDK code
- Use AWS Secrets Manager or SSM Parameter Store for sensitive values
- Apply least-privilege IAM policies
- Enable encryption at rest for all data stores
- Use VPCs for network isolation where appropriate
- Enable CloudTrail and access logging
