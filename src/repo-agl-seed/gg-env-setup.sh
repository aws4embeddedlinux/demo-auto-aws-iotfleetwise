#! /bin/bash

source ./config

if [ -z "$AWS_DEFAULT_REGION" ]; then
  echo "AWS_DEFAULT_REGION is required"
  exit 0
fi

if [ -z "$THING_NAME" ]; then
  echo "THING_NAME is required"
  exit 0
fi

if [ -z "$THING_GROUP_NAME" ]; then
  echo "THING_GROUP_NAME is required"
  exit 0
fi

if ! aws --output text iot list-thing-groups --query 'thingGroups[].groupName' | grep -q "${THING_GROUP_NAME}"; then
  echo "Thing Group with name \"${THING_GROUP_NAME}\" does not exist. Creating AWS resources"
  aws iot create-thing-group --thing-group-name "${THING_GROUP_NAME}"
fi

if ! aws iot describe-thing --thing-name "${THING_NAME}" > /dev/null 2>&1; then
  echo "Thing with name \"${THING_NAME}\" does not exist. Creating AWS resources"

  echo "Creating Thing in IoT Thing Registry"
  aws --output text iot create-thing \
    --thing-name "${THING_NAME}" \
    --query 'thingArn'

  echo "Adding Thing to the \"${THING_GROUP_NAME}\" Group"
  aws iot add-thing-to-thing-group --thing-name "${THING_NAME}" \
    --thing-group-name ${THING_GROUP_NAME}
else
  echo "Thing with name \"${THING_NAME}\" already exists - skipping resource creation"
fi

if [ ! -d $CERTS_DIR ]; then
  mkdir -p $CERTS_DIR
fi

# Check to see if root CA file exists, download if not
if [ ! -f $ROOT_CERT_PATH ]; then
  printf "\nDownloading AWS IoT Root CA certificate from AWS...\n"
  curl https://www.amazontrust.com/repository/AmazonRootCA1.pem > $ROOT_CERT_PATH
fi

if [ ! -f $DEVICE_CERT_PATH ]; then
  echo "Creating Keys and Certificate"
  CERTIFICATE_ARN=$(aws --output text iot create-keys-and-certificate \
    --set-as-active \
    --certificate-pem-outfile "$DEVICE_CERT_PATH" \
    --public-key-outfile "$PUBLIC_KEY_PATH" \
    --private-key-outfile "$PRIVATE_KEY_PATH" \
    --query 'certificateArn')

  THING_POLICY_OUTPUT="{
      \"Version\": \"2012-10-17\",
      \"Statement\": [
        {
          \"Effect\": \"Allow\",
          \"Action\": [
            \"iot:Publish\",
            \"iot:Receive\"
          ],
          \"Resource\": [\"arn:aws:iot:$AWS_DEFAULT_REGION:$ACCOUNT_ID:topic/*\"]
        },
        {
          \"Effect\": \"Allow\",
          \"Action\": [\"iot:Subscribe\"],
          \"Resource\": [\"arn:aws:iot:$AWS_DEFAULT_REGION:$ACCOUNT_ID:topicfilter/*\"]
        },
        {
          \"Effect\": \"Allow\",
          \"Action\": [\"iot:Connect\"],
          \"Resource\":[ \"*\" ],
            \"Condition\": {
                \"Bool\": {
                    \"iot:Connection.Thing.IsAttached\": [\"true\"]
                }
            }
        },
        {
          \"Effect\": \"Allow\",
          \"Action\": [\"greengrass:*\"],
          \"Resource\":[ \"*\" ]
        }
      ]
    }"

  echo "Generating Thing Policy document"
  echo "$THING_POLICY_OUTPUT" | tee "${RUN_DIR}"/thing-policy.json >/dev/null

  echo "Creating Thing Policy"
  aws iot create-policy \
    --policy-name "$THING_POLICY_NAME" \
    --policy-document file://"${RUN_DIR}"/thing-policy.json

  echo "Attaching Thing Policy to Thing Certificate"
  aws iot attach-policy \
    --policy-name "$THING_POLICY_NAME" \
    --target "${CERTIFICATE_ARN}"

  echo "Attaching Thing Principal (Certificate)"
  aws iot attach-thing-principal \
    --thing-name "${THING_NAME}" \
    --principal "${CERTIFICATE_ARN}"
    
  GREENGRASS_TES_ROLE_ALIAS_POLICY_OUTPUT="{
      \"Version\": \"2012-10-17\",
      \"Statement\": [
        {
          \"Effect\": \"Allow\",
          \"Action\": [
            \"iot:AssumeRoleWithCertificate\"
          ],
          \"Resource\": [\"arn:aws:iot:$AWS_DEFAULT_REGION:$ACCOUNT_ID:rolealias/GreengrassCoreTokenExchangeRoleAlias\"]
        }
      ]
    }"

  echo "Generating Greengrass Role Alias Policy document"
  echo "$GREENGRASS_TES_ROLE_ALIAS_POLICY_OUTPUT" | tee "${RUN_DIR}"/gg-iot-role-alias-policy.json >/dev/null

  echo "Creating Greengrass Role Alias Policy"
  aws iot create-policy \
    --policy-name "$GREENGRASS_TES_ROLE_ALIAS_POLICY_NAME" \
    --policy-document file://"${RUN_DIR}"/thing-policy.json

  echo "Attaching Greengrass Role Alias  Policy to Thing Certificate"
  aws iot attach-policy \
    --policy-name "$GREENGRASS_TES_ROLE_ALIAS_POLICY_NAME" \
    --target "${CERTIFICATE_ARN}"

fi

echo "Generating local.conf"
cat <<EOT > local.conf
$LOCAL_CONF
EOT
