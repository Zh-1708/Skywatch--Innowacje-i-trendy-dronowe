---
name: aws-cost-operations
description: Optimize AWS costs and manage cloud spending. Use when the user asks to reduce AWS costs, analyze cloud spending, review billing, set up budgets, or find cost optimization opportunities.
metadata:
  author: zxkane
  version: "1.0.0"
---

# AWS Cost Operations

Help users optimize AWS costs, analyze spending patterns, and implement cost-saving strategies.

## Cost Analysis Commands

### View Current Costs
```bash
# Get cost and usage for current month
aws ce get-cost-and-usage \
  --time-period Start=$(date -d "$(date +%Y-%m-01)" +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics "BlendedCost" "UnblendedCost" "UsageQuantity"

# Break down by service
aws ce get-cost-and-usage \
  --time-period Start=$(date -d "$(date +%Y-%m-01)" +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics "BlendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE
```

### Cost Forecast
```bash
aws ce get-cost-forecast \
  --time-period Start=$(date +%Y-%m-%d),End=$(date -d "+30 days" +%Y-%m-%d) \
  --metric BLENDED_COST \
  --granularity MONTHLY
```

## Common Cost Optimization Strategies

### 1. Right-Sizing EC2 Instances
```bash
# Get EC2 rightsizing recommendations
aws ce get-rightsizing-recommendation \
  --service AmazonEC2 \
  --configuration RecommendationTarget=SAME_INSTANCE_FAMILY,BenefitsConsidered=true
```

### 2. Unused Resources Audit

Check for:
- **Unattached EBS volumes**: `aws ec2 describe-volumes --filters Name=status,Values=available`
- **Unused Elastic IPs**: `aws ec2 describe-addresses` (look for unassociated IPs)
- **Idle load balancers**: Check CloudWatch for ALBs with zero requests
- **Old snapshots**: `aws ec2 describe-snapshots --owner-ids self --query 'sort_by(Snapshots, &StartTime)'`

### 3. S3 Cost Optimization

- Enable S3 Intelligent-Tiering for unpredictable access patterns
- Set lifecycle policies to transition objects to cheaper storage classes
- Enable S3 Storage Lens for visibility into usage patterns

```bash
# Check bucket sizes
aws s3 ls --summarize --human-readable --recursive s3://bucket-name/
```

### 4. Lambda Optimization

- Right-size memory allocation (use AWS Lambda Power Tuning)
- Use ARM64 (Graviton) for ~20% cost savings
- Set appropriate timeout values
- Use provisioned concurrency only when needed

### 5. Reserved Instances & Savings Plans

```bash
# Get Savings Plans recommendations
aws ce get-savings-plans-purchase-recommendation \
  --savings-plans-type COMPUTE_SP \
  --term-in-years ONE_YEAR \
  --payment-option NO_UPFRONT \
  --lookback-period-in-days SIXTY_DAYS
```

## Budget Alerts

### Create a Monthly Budget
```bash
aws budgets create-budget \
  --account-id $AWS_ACCOUNT_ID \
  --budget '{
    "BudgetName": "Monthly-Budget",
    "BudgetLimit": {"Amount": "1000", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }' \
  --notifications-with-subscribers '[{
    "Notification": {
      "NotificationType": "ACTUAL",
      "ComparisonOperator": "GREATER_THAN",
      "Threshold": 80,
      "ThresholdType": "PERCENTAGE"
    },
    "Subscribers": [{
      "SubscriptionType": "EMAIL",
      "Address": "team@example.com"
    }]
  }]'
```

## CDK Cost Patterns

### Apply cost tags to all resources
```typescript
import * as cdk from "aws-cdk-lib";

const app = new cdk.App();
const stack = new MyStack(app, "MyStack");

cdk.Tags.of(stack).add("Environment", "production");
cdk.Tags.of(stack).add("CostCenter", "engineering");
cdk.Tags.of(stack).add("Project", "my-project");
```

### Use cost-effective defaults
```typescript
// DynamoDB: PAY_PER_REQUEST for variable workloads
new dynamodb.Table(this, "Table", {
  billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
  // ...
});

// Lambda: ARM64 architecture for cost savings
new lambda.Function(this, "Fn", {
  architecture: lambda.Architecture.ARM_64,
  // ...
});
```

## Checklist

- [ ] Enable AWS Cost Explorer
- [ ] Set up billing alerts and budgets
- [ ] Review and terminate unused resources monthly
- [ ] Use Savings Plans or Reserved Instances for steady-state workloads
- [ ] Enable S3 lifecycle policies
- [ ] Right-size compute resources quarterly
- [ ] Tag all resources for cost allocation
- [ ] Review data transfer costs
