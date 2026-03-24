---
name: aws-serverless-eda
description: Build serverless and event-driven architectures on AWS. Use when the user asks to create serverless applications, set up event-driven systems, work with Lambda, EventBridge, Step Functions, or build microservices on AWS.
metadata:
  author: zxkane
  version: "1.0.0"
---

# AWS Serverless & Event-Driven Architecture

Help users build serverless applications and event-driven architectures on AWS.

## Core Services

| Service | Purpose |
|---------|---------|
| **Lambda** | Compute — run code without managing servers |
| **EventBridge** | Event bus — route events between services |
| **Step Functions** | Orchestration — coordinate multi-step workflows |
| **SQS** | Queuing — decouple producers from consumers |
| **SNS** | Pub/Sub — fan-out notifications to subscribers |
| **API Gateway** | HTTP API — expose Lambda functions as REST/HTTP APIs |
| **DynamoDB** | Database — serverless NoSQL with single-digit ms latency |

## Event-Driven Patterns

### 1. EventBridge Event Bus

```typescript
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";

const bus = new events.EventBus(this, "AppBus", {
  eventBusName: "my-app-bus",
});

// Rule: route order events to processing Lambda
new events.Rule(this, "OrderCreatedRule", {
  eventBus: bus,
  eventPattern: {
    source: ["my-app.orders"],
    detailType: ["OrderCreated"],
  },
  targets: [new targets.LambdaFunction(orderProcessorFn)],
});
```

### Publishing Events
```typescript
import { EventBridgeClient, PutEventsCommand } from "@aws-sdk/client-eventbridge";

const client = new EventBridgeClient({});

await client.send(new PutEventsCommand({
  Entries: [{
    Source: "my-app.orders",
    DetailType: "OrderCreated",
    Detail: JSON.stringify({ orderId: "123", amount: 99.99 }),
    EventBusName: "my-app-bus",
  }],
}));
```

### 2. SQS Queue Processing

```typescript
import * as sqs from "aws-cdk-lib/aws-sqs";
import * as lambdaEventSources from "aws-cdk-lib/aws-lambda-event-sources";

const queue = new sqs.Queue(this, "ProcessingQueue", {
  visibilityTimeout: cdk.Duration.seconds(300),
  deadLetterQueue: {
    queue: dlq,
    maxReceiveCount: 3,
  },
});

processorFn.addEventSource(
  new lambdaEventSources.SqsEventSource(queue, {
    batchSize: 10,
    maxBatchingWindow: cdk.Duration.seconds(5),
  })
);
```

### 3. Step Functions Workflow

```typescript
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import * as tasks from "aws-cdk-lib/aws-stepfunctions-tasks";

const validateOrder = new tasks.LambdaInvoke(this, "ValidateOrder", {
  lambdaFunction: validateFn,
  outputPath: "$.Payload",
});

const processPayment = new tasks.LambdaInvoke(this, "ProcessPayment", {
  lambdaFunction: paymentFn,
  outputPath: "$.Payload",
});

const sendConfirmation = new tasks.LambdaInvoke(this, "SendConfirmation", {
  lambdaFunction: notifyFn,
});

const definition = validateOrder
  .next(new sfn.Choice(this, "IsValid?")
    .when(sfn.Condition.booleanEquals("$.valid", true),
      processPayment.next(sendConfirmation))
    .otherwise(new sfn.Fail(this, "OrderInvalid", {
      cause: "Order validation failed",
    })));

new sfn.StateMachine(this, "OrderWorkflow", {
  definitionBody: sfn.DefinitionBody.fromChainable(definition),
  timeout: cdk.Duration.minutes(5),
});
```

### 4. API Gateway + Lambda

```typescript
import * as apigw from "aws-cdk-lib/aws-apigatewayv2";
import * as integrations from "aws-cdk-lib/aws-apigatewayv2-integrations";

const httpApi = new apigw.HttpApi(this, "HttpApi", {
  corsPreflight: {
    allowOrigins: ["*"],
    allowMethods: [apigw.CorsHttpMethod.GET, apigw.CorsHttpMethod.POST],
  },
});

httpApi.addRoutes({
  path: "/orders",
  methods: [apigw.HttpMethod.POST],
  integration: new integrations.HttpLambdaIntegration("CreateOrder", createOrderFn),
});
```

## Lambda Best Practices

### Handler Pattern
```typescript
import { SQSEvent, SQSRecord } from "aws-lambda";

export const handler = async (event: SQSEvent): Promise<void> => {
  const failedRecords: string[] = [];

  for (const record of event.Records) {
    try {
      await processRecord(record);
    } catch (error) {
      console.error(`Failed to process record ${record.messageId}`, error);
      failedRecords.push(record.messageId);
    }
  }

  // Partial batch failure reporting
  if (failedRecords.length > 0) {
    return {
      batchItemFailures: failedRecords.map(id => ({
        itemIdentifier: id,
      })),
    } as any;
  }
};

async function processRecord(record: SQSRecord): Promise<void> {
  const body = JSON.parse(record.body);
  // Process the message...
}
```

### Environment Configuration
```typescript
new lambda.Function(this, "Fn", {
  runtime: lambda.Runtime.NODEJS_20_X,
  architecture: lambda.Architecture.ARM_64,
  handler: "index.handler",
  code: lambda.Code.fromAsset("lambda"),
  memorySize: 256,
  timeout: cdk.Duration.seconds(30),
  tracing: lambda.Tracing.ACTIVE,
  environment: {
    TABLE_NAME: table.tableName,
    BUS_NAME: bus.eventBusName,
    LOG_LEVEL: "INFO",
  },
});
```

## Design Principles

1. **Single responsibility** — Each Lambda handles one operation
2. **Idempotency** — Design all handlers to be safely retried
3. **Dead letter queues** — Always configure DLQs for async invocations
4. **Partial batch failures** — Report individual failures, not whole-batch failures
5. **Observability** — Enable X-Ray tracing and structured logging
6. **Least privilege** — Grant only required IAM permissions
7. **Event schema validation** — Validate event payloads at the boundary
8. **Graceful degradation** — Use circuit breakers and fallbacks for downstream calls
