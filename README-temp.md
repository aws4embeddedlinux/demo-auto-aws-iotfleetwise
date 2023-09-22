`npm install -g aws-cdk`

Ensure correct account, region and exported keys.

`cdk bootstrap`

`cd demo-auto-aws-iotfleetwise`

`python3 -m venv .venv`

`source .venv/bin/activate`

`pip install -r requirements.txt`

`cdk deploy --all --require-approval never`