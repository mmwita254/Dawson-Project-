import * as cdk from 'aws-cdk-lib';
import { Stack, StackProps } from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as lambda_event_sources from 'aws-cdk-lib/aws-lambda-event-sources';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import { BuildSpec } from 'aws-cdk-lib/aws-codebuild';
import { Construct } from 'constructs';

interface BackendStackProps extends StackProps {
  OPENAI_MODEL_ID?: string;
  OPENAI_EMBEDDING_ID?: string;
  OPENAI_API_KEY?: string;
}

export class BackendStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: BackendStackProps) {
    super(scope, id, props);

    const {
      OPENAI_MODEL_ID = process.env.OPENAI_MODEL_ID ?? 'gpt-4o',
      OPENAI_EMBEDDING_ID = process.env.OPENAI_EMBEDDING_ID ??
        'text-embedding-ada-002',
      OPENAI_API_KEY = process.env.OPENAI_API_KEY ?? '',
    } = props;

    // create the document bucket
    const bucket = new s3.Bucket(this, 'DocumentBucket', {
      bucketName: `${this.stackName.toLowerCase()}-${this.region}-${
        this.account
      }`,
      versioned: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      publicReadAccess: false,
      cors: [
        {
          allowedOrigins: ['*'],
          allowedMethods: [
            s3.HttpMethods.GET,
            s3.HttpMethods.PUT,
            s3.HttpMethods.POST,
            s3.HttpMethods.DELETE,
          ],
          allowedHeaders: ['*'],
        },
      ],
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    });

    // define the bucket policy to deny non-https access
    const bucketPolicy = new iam.PolicyStatement({
      sid: 'EnforceHTTPSSid',
      effect: iam.Effect.DENY,
      principals: [new iam.AnyPrincipal()],
      actions: ['s3:*'],
      resources: [bucket.bucketArn, `${bucket.bucketArn}/*`],
      conditions: {
        Bool: {
          'aws:SecureTransport': 'false',
        },
      },
    });

    bucket.addToResourcePolicy(bucketPolicy);

    // create the embedding queue
    const embeddingQueue = new sqs.Queue(this, 'EmbeddingQueue', {
      visibilityTimeout: cdk.Duration.seconds(300),
      retentionPeriod: cdk.Duration.hours(1),
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    //create the embedding queue policy
    embeddingQueue.addToResourcePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['sqs:SendMessage'],
        resources: [embeddingQueue.queueArn],
        principals: [new iam.ServicePrincipal('lambda.amazonaws.com')],
      }),
    );

    // Document table
    const documentTable = new dynamodb.Table(this, 'DocumentTable', {
      partitionKey: { name: 'userid', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'documentid', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // Corresponds to DeletionPolicy: Delete
    });

    //Memory table
    const memoryTable = new dynamodb.Table(this, 'MemoryTable', {
      partitionKey: { name: 'SessionId', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // Corresponds to DeletionPolicy: Delete
    });

    // Project table
    const projectTable = new dynamodb.Table(this, 'ProjectTable', {
      partitionKey: { name: 'userid', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'projectid', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // Corresponds to DeletionPolicy: Delete
    });

    // Add additional attributes to store documents and chat sessions
    projectTable.addGlobalSecondaryIndex({
      indexName: 'ProjectIndex',
      partitionKey: { name: 'projectid', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'created', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });
  }
}
