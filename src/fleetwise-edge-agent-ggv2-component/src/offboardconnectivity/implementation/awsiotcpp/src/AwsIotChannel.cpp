/**
 * Copyright 2020 Amazon.com, Inc. and its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
 * Licensed under the Amazon Software License (the "License").
 * You may not use this file except in compliance with the License.
 * A copy of the License is located at
 * http://aws.amazon.com/asl/
 * or in the "license" file accompanying this file. This file is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
 * express or implied. See the License for the specific language governing
 * permissions and limitations under the License.
 */

#include "AwsIotChannel.h"
#include "AwsIotConnectivityModule.h"
#include "TraceModule.h"
#include <sstream>
#include <functional>

using namespace Aws::IoTFleetWise::OffboardConnectivityAwsIot;
using namespace Aws::IoTFleetWise::OffboardConnectivity;
using namespace Aws::Crt;
using namespace Aws::Greengrass;

// Pure virtual destructor needs to be defined somewhere
Aws::IoTFleetWise::OffboardConnectivity::IReceiverCallback::~IReceiverCallback()
{
}

IConnectivityModule::~IConnectivityModule()
{
}

AwsIotChannel::AwsIotChannel( IConnectivityModule *connectivityModule,
                              const std::shared_ptr<PayloadManager> &payloadManager )
    : mConnectivityModule( connectivityModule )
    , mPayloadManager( payloadManager )
    , mTopicName()
    , mSubscribed( false )
    , mSubscribeAsynchronously( false )
{

}

bool
AwsIotChannel::isAlive()
{
    std::lock_guard<std::mutex> connectivityLock( mConnectivityMutex );
    return isAliveNotThreadSafe();
}

bool
AwsIotChannel::isAliveNotThreadSafe()
{
    if ( mConnectivityModule == nullptr )
    {
        return false;
    }
    return mConnectivityModule->isAlive();
}

void
AwsIotChannel::setTopic( const std::string &topicNameRef, bool subscribeAsynchronously )
{
    if ( topicNameRef.empty() )
    {
        mLogger.error( "AwsIotChannel::setTopic", "Empty ingestion topic name provided" );
    }
    mSubscribeAsynchronously = subscribeAsynchronously;
    mTopicName = topicNameRef;
}

ConnectivityError
AwsIotChannel::subscribe()
{
    std::lock_guard<std::mutex> connectivityLock( mConnectivityMutex );
    if ( !isTopicValid() )
    {
        mLogger.error( "AwsIotChannel::subscribe", "Empty ingestion topic name provided" );
        return ConnectivityError::NotConfigured;
    }
    if ( !isAliveNotThreadSafe() )
    {
        mLogger.error( "AwsIotChannel::subscribe", "MQTT Connection not established, failed to subscribe" );
        return ConnectivityError::NoConnection;
    }
    auto connection = mConnectivityModule->getConnection();

    mSubscribeStreamHandler = std::make_shared<SubscribeStreamHandler>([&](uint8_t* data, size_t size) {
        notifyListeners<const std::uint8_t *, size_t>(
            &IReceiverCallback::onDataReceived, data, size );
    });
    mSubscribeOperation = connection->NewSubscribeToIoTCore(mSubscribeStreamHandler);
    SubscribeToIoTCoreRequest subscribeRequest;
    subscribeRequest.SetQos(QOS_AT_LEAST_ONCE);
    subscribeRequest.SetTopicName(mTopicName.c_str());

    fprintf(stdout, "Attempting to subscribe to %s topic\n", mTopicName.c_str());
    auto requestStatus = mSubscribeOperation->Activate(subscribeRequest).get();
    if (!requestStatus)
    {
        fprintf(stderr, "Failed to send subscription request to %s topic\n", mTopicName.c_str());
        return ConnectivityError::NoConnection;
    }

    auto subscribeResultFuture = mSubscribeOperation->GetResult();

    // To avoid throwing exceptions, wait on the result for a specified timeout:
    if (subscribeResultFuture.wait_for(std::chrono::seconds(10)) == std::future_status::timeout)
    {
        fprintf(stderr, "Timed out while waiting for response from Greengrass Core\n");
        return ConnectivityError::NoConnection;
    }

    auto subscribeResult = subscribeResultFuture.get();
    if (subscribeResult)
    {
        fprintf(stdout, "Successfully subscribed to %s topic\n", mTopicName.c_str());
    }
    else
    {
        auto errorType = subscribeResult.GetResultType();
        if (errorType == OPERATION_ERROR)
        {
            OperationError *error = subscribeResult.GetOperationError();
            /*
             * This pointer can be casted to any error type like so:
             * if(error->GetModelName() == UnauthorizedError::MODEL_NAME)
             *    UnauthorizedError *unauthorizedError = static_cast<UnauthorizedError*>(error);
             */
            if (error->GetMessage().has_value())
                fprintf(stderr, "Greengrass Core responded with an error: %s\n", error->GetMessage().value().c_str());
        }
        else
        {
            fprintf(
                stderr,
                "Attempting to receive the response from the server failed with error code %s\n",
                subscribeResult.GetRpcError().StatusToString().c_str());
        }
        return ConnectivityError::NoConnection;
    }

    return ConnectivityError::Success;
}

size_t
AwsIotChannel::getMaxSendSize() const
{
    return AWS_IOT_MAX_MESSAGE_SIZE;
}

ConnectivityError
AwsIotChannel::send( const std::uint8_t *buf, size_t size, struct CollectionSchemeParams collectionSchemeParams )
{
    std::lock_guard<std::mutex> connectivityLock( mConnectivityMutex );
    if ( !isTopicValid() )
    {
        mLogger.warn( "AwsIotChannel::send", "Invalid topic provided" );
        return ConnectivityError::NotConfigured;
    }

    if ( buf == nullptr || size == 0 )
    {
        mLogger.warn( "AwsIotChannel::send", "No valid data provided" );
        return ConnectivityError::WrongInputData;
    }

    if ( size > getMaxSendSize() )
    {
        mLogger.warn( "AwsIotChannel::send", "Payload provided is too long" );
        return ConnectivityError::WrongInputData;
    }

    if ( !isAliveNotThreadSafe() )
    {
        mLogger.warn( "AwsIotChannel::send", "No alive IPC Connection." );
        if ( mPayloadManager != nullptr )
        {
            bool isDataPersisted = mPayloadManager->storeData( buf, size, collectionSchemeParams );

            if ( isDataPersisted )
            {
                mLogger.trace( "AwsIotChannel::send", "Payload has persisted successfully on disk" );
            }
            else
            {
                mLogger.warn( "AwsIotChannel::send", "Payload has not been persisted" );
            }
        }
        return ConnectivityError::NoConnection;
    }

    auto connection = mConnectivityModule->getConnection();

    auto publishOperation = connection->NewPublishToIoTCore();
    PublishToIoTCoreRequest publishRequest;
    publishRequest.SetTopicName(mTopicName.c_str());
    Vector<uint8_t> payload(buf, buf+size);
    publishRequest.SetPayload(payload);
    publishRequest.SetQos(QOS_AT_LEAST_ONCE);

    fprintf(stdout, "Attempting to publish to %s topic\n", mTopicName.c_str());
    auto requestStatus = publishOperation->Activate(publishRequest).get();
    if (!requestStatus)
    {
        fprintf(
            stderr,
            "Failed to publish to %s topic with error %s\n",
            mTopicName.c_str(),
            requestStatus.StatusToString().c_str());
        return ConnectivityError::NoConnection;
    }

    auto publishResultFuture = publishOperation->GetResult();

    // To avoid throwing exceptions, wait on the result for a specified timeout:
    if (publishResultFuture.wait_for(std::chrono::seconds(10)) == std::future_status::timeout)
    {
        fprintf(stderr, "Timed out while waiting for response from Greengrass Core\n");
        return ConnectivityError::NoConnection;
    }

    auto publishResult = publishResultFuture.get();
    if (publishResult)
    {
        fprintf(stdout, "Successfully published to %s topic\n", mTopicName.c_str());
        auto *response = publishResult.GetOperationResponse();
        (void)response;
    }
    else
    {
        auto errorType = publishResult.GetResultType();
        if (errorType == OPERATION_ERROR)
        {
            OperationError *error = publishResult.GetOperationError();
            /*
             * This pointer can be casted to any error type like so:
             * if(error->GetModelName() == UnauthorizedError::MODEL_NAME)
             *    UnauthorizedError *unauthorizedError = static_cast<UnauthorizedError*>(error);
             */
            if (error->GetMessage().has_value())
                fprintf(stderr, "Greengrass Core responded with an error: %s\n", error->GetMessage().value().c_str());
        }
        else
        {
            fprintf(
                stderr,
                "Attempting to receive the response from the server failed with error code %s\n",
                publishResult.GetRpcError().StatusToString().c_str());
        }
        return ConnectivityError::NoConnection;
    }

    return ConnectivityError::Success;
}

bool
AwsIotChannel::unsubscribe()
{
    std::lock_guard<std::mutex> connectivityLock( mConnectivityMutex );
    if ( mSubscribed && isAliveNotThreadSafe() )
    {
        auto connection = mConnectivityModule->getConnection();

        // TODO

        return true;
    }
    return false;
}

AwsIotChannel::~AwsIotChannel()
{
    unsubscribe();
}
