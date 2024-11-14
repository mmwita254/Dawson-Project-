# Dawson-Project-
GPT for Dawson Group that harnesses Generative AI for information retrieval. 

## Key features

- [OpenAI](https://openai.com/) for serverless embedding and inference
- [LangChain](https://github.com/hwchase17/langchain) to orchestrate a Q&A LLM chain
- [FAISS](https://github.com/facebookresearch/faiss) vector store
- [Amazon DynamoDB](https://aws.amazon.com/dynamodb/) for serverless conversational memory
- [AWS Lambda](https://aws.amazon.com/lambda/) for serverless compute
- Frontend built in [React](https://react.dev/), [TypeScript](https://www.typescriptlang.org/), [TailwindCSS](https://tailwindcss.com/), and [Vite](https://vitejs.dev/).
- Run locally or deploy to [AWS Amplify Hosting](https://aws.amazon.com/amplify/hosting/)
- [Amazon Cognito](https://aws.amazon.com/cognito/) for authentication


## How the application works

![Serverless PDF Chat architecture](updated_architecture.jpg "Serverless PDF Chat architecture")

1. A user uploads a PDF document into an [Amazon Simple Storage Service](https://aws.amazon.com/s3/) (S3) bucket through a static web application frontend.
1. This upload triggers a metadata extraction and document embedding process. The process converts the text in the document into vectors. The vectors are loaded into a vector index and stored in S3 for later use.
1. When a user chats with a PDF document and sends a prompt to the backend, a Lambda function retrieves the index from S3 and searches for information related to the prompt.
1. A LLM then uses the results of this vector search, previous messages in the conversation, and its general-purpose capabilities to formulate a response to the user.


## Deployment instructions

### Prerequisites

- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- [Python](https://www.python.org/) 3.11 or greater

### Cloning the repository

Clone this repository:

```bash
git clone https://github.com/mmwita254/Dawson-Project-.git
```

### Deploy the frontend with AWS Amplify Hosting

[AWS Amplify Hosting](https://aws.amazon.com/amplify/hosting/) enables a fully-managed deployment of the application's React frontend in an AWS-managed account using Amazon S3 and [Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html). You can optionally run the React frontend locally by skipping to [Deploy the application with AWS SAM](#Deploy-the-application-with-AWS-SAM).

To set up Amplify Hosting:

1. Fork this GitHub repository and take note of your repository URL, for example `https://github.com/mmwita254/Dawson-Project-`.
1. Create a GitHub fine-grained access token for the new repository by following [this guide](https://docs.aws.amazon.com/amplify/latest/userguide/setting-up-GitHub-access.html). For the **Repository permissions**, select **Read and write** for **Content** and **Webhooks**.
1. Create a new secret called `dawson-project-github-token` in AWS Secrets Manager and input your fine-grained access token as plaintext. Select the **Plaintext** tab and confirm your secret looks like this:

   ```json
   github_pat_T2wyo------------------------------------------------------------------------rs0Pp
   ```

### Deploy the application with AWS SAM

1. Change to the `backend` directory and [build](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-cli-command-reference-sam-build.html) the application:

   ```bash
   cd backend
   sam build
   ```

1. [Deploy](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-cli-command-reference-sam-deploy.html) the application into your AWS account:

   ```bash
   sam deploy --guided
   ```

1. For **Stack Name**, choose `dawson-project`.

1. For **Frontend**, specify the environment ("local", "amplify") for the frontend of the application.

1. If you selected "amplify", specify the URL of the forked Git repository containing the application code.

1. Specify the OpenAI model ID. For example, `gpt-4o`.

1. Specify the OpenAI API key

1. For the remaining options, keep the defaults by pressing the enter key.

AWS SAM will now provision the AWS resources defined in the `backend/template.yaml` template. Once the deployment is completed successfully, you will see a set of output values similar to the following:

```bash
CloudFormation outputs from deployed stack
-------------------------------------------------------------------------------
Outputs
-------------------------------------------------------------------------------
Key                 CognitoUserPool
Description         -
Value               us-east-1_gxKtRocFs

Key                 CognitoUserPoolClient
Description         -
Value               874ghcej99f8iuo0lgdpbrmi76k

Key                 ApiGatewayBaseUrl
Description         -
Value               https://abcd1234.execute-api.us-east-1.amazonaws.com/dev/
-------------------------------------------------------------------------------
```

If you selected to deploy the React frontend using Amplify Hosting, navigate to the Amplify console to check the build status. If the build does not start automatically, trigger it through the Amplify console.

If you selected to run the React frontend locally and connect to the deployed resources in AWS, you will use the CloudFormation stack outputs in the following section.

### Optional: Run the React frontend locally

Create a file named `.env.development` in the `frontend` directory. [Vite will use this file](https://vitejs.dev/guide/env-and-mode.html) to set up environment variables when we run the application locally.

Copy the following file content and replace the values with the outputs provided by AWS SAM:

```plaintext
VITE_REGION=us-east-1
VITE_API_ENDPOINT=https://abcd1234.execute-api.us-east-1.amazonaws.com/dev/
VITE_USER_POOL_ID=us-east-1_gxKtRocFs
VITE_USER_POOL_CLIENT_ID=874ghcej99f8iuo0lgdpbrmi76k
```

Next, install the frontend's dependencies by running the following command in the `frontend` directory:

```bash
npm install
```

Finally, to start the application locally, run the following command in the `frontend` directory:

```bash
npm run dev
```

Vite will now start the application under `http://localhost:5173`.

### Create a user in the Amazon Cognito user pool

The application uses Amazon Cognito to authenticate users through a login screen. In this step, you will create a user to access the application.

Perform the following steps to create a user in the Cognito user pool:

1. Navigate to the **Amazon Cognito console**.
1. Find the user pool with an ID matching the output provided by AWS SAM above.
1. Under Users, choose **Create user**.
1. Enter an email address and a password that adheres to the password requirements.
1. Choose **Create user**.

Navigate back to your Amplify website URL or local host address to log in with the new user's credentials.

## Cleanup

1. Delete any secrets in AWS Secrets Manager created as part of this walkthrough.
1. [Empty the Amazon S3 bucket](https://docs.aws.amazon.com/AmazonS3/latest/userguide/empty-bucket.html) created as part of the AWS SAM template.
1. Run the following command in the `backend` directory of the project to delete all associated resources resources:

   ```bash
   sam delete
   ```

## Credits

This project was based on work from [ServerlessPDFChat](https://github.com/aws-samples/serverless-pdf-chat).

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.
