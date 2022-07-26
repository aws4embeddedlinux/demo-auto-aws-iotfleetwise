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

#pragma once

// Includes
#include "IReceiver.h"
#include "ISender.h"
#include "LoggingModule.h"
#include "PayloadManager.h"
#include <atomic>
#include <aws/greengrass/GreengrassCoreIpcClient.h>
#include <memory>
#include <mutex>
#include <string>

namespace Aws
{
namespace IoTFleetWise
{
/**
 * @brief Namespace depending on Aws Iot SDK headers
 */
namespace OffboardConnectivityAwsIot
{

using namespace Aws::Greengrass;

class IConnectivityModule
{
public:
    virtual std::shared_ptr<GreengrassCoreIpcClient> getConnection() const = 0;

    virtual bool isAlive() const = 0;

    virtual ~IConnectivityModule() = 0;
};

using Aws::IoTFleetWise::OffboardConnectivity::CollectionSchemeParams;
using Aws::IoTFleetWise::OffboardConnectivity::ConnectivityError;

using SubscribeCallback = std::function<void(uint8_t *, size_t)>;

class SubscribeStreamHandler : public SubscribeToIoTCoreStreamHandler
{
public:
    SubscribeStreamHandler(SubscribeCallback callback) : mCallback(callback) {

    }
private:
    void OnStreamEvent(IoTCoreMessage *response) override
    {
        auto message = response->GetMessage();

        if (message.has_value() && message.value().GetPayload().has_value())
        {
            auto payloadBytes = message.value().GetPayload().value();
            std::string payloadString(payloadBytes.begin(), payloadBytes.end());
            fprintf(stdout, "Received %zu bytes\n", payloadString.size());
            mCallback(payloadBytes.data(), payloadBytes.size());
        }
    };
    SubscribeCallback mCallback;
};

/**
 * @brief a channel that can be used as IReceiver or ISender or both
 *
 * If the Channel should be used for receiving data subscribe must be called.
 * setTopic must be called always. There can be multiple AwsIotChannels
 * from one AwsIotConnectivityModule. The channel of the connectivityModule passed in the
 * constructor must be established before anything meaningful can be done with this class
 * @see AwsIotConnectivityModule
 */
class AwsIotChannel : public Aws::IoTFleetWise::OffboardConnectivity::ISender,
                      public Aws::IoTFleetWise::OffboardConnectivity::IReceiver
{
public:

    AwsIotChannel( IConnectivityModule *connectivityModule,
                   const std::shared_ptr<PayloadManager> &payloadManager );
    ~AwsIotChannel();

    /**
     * @brief the topic must be set always before using any functionality of this class
     * @param topicNameRef MQTT topic that will be used for sending or receiving data
     *                      if subscribe was called
     * @param subscribeAsynchronously if true the channel will be subscribed to the topic asynchronously so that the
     * channel can receive data
     *
     */
    void setTopic( const std::string &topicNameRef, bool subscribeAsynchronously = false );

    /**
     * @brief Subscribe to the MQTT topic from setTopic. Necessary if data is received on the topic
     *
     * This function blocks until subscribe succeeded or failed and should be done in the setup form
     * the bootstrap thread. The connection of the connectivityModule passed in the constructor
     * must be established otherwise subscribe will fail. No retries are done to try to subscribe
     * this needs to be done in the boostrap during the setup.
     * @return Success if subscribe finished correctly
     */
    ConnectivityError subscribe();

    /**
     * @brief After unsubscribe no data will be received over the channel
     */
    bool unsubscribe();

    bool isAlive() override;

    size_t getMaxSendSize() const override;

    ConnectivityError send( const std::uint8_t *buf,
                            size_t size,
                            struct CollectionSchemeParams collectionSchemeParams = CollectionSchemeParams() ) override;

    bool
    isTopicValid()
    {
        return !mTopicName.empty();
    }

    void
    invalidateConnection()
    {
        std::lock_guard<std::mutex> connectivityLock( mConnectivityMutex );
        std::lock_guard<std::mutex> connectivityLambdaLock( mConnectivityLambdaMutex );
        mConnectivityModule = nullptr;
    }

    bool
    shouldSubscribeAsynchronously()
    {
        return mSubscribeAsynchronously;
    }

private:
    bool isAliveNotThreadSafe();

    /** See "Message size" : "The payload for every publish request can be no larger
     * than 128 KB. AWS IoT Core rejects publish and connect requests larger than this size."
     * https://docs.aws.amazon.com/general/latest/gr/iot-core.html#limits_iot
     */
    static const size_t AWS_IOT_MAX_MESSAGE_SIZE = 131072; // = 128 KiB
    IConnectivityModule *mConnectivityModule;
    std::mutex mConnectivityMutex;
    std::mutex mConnectivityLambdaMutex;
    std::shared_ptr<PayloadManager> mPayloadManager;
    std::string mTopicName;
    std::atomic<bool> mSubscribed;
    Aws::IoTFleetWise::Platform::LoggingModule mLogger;
    std::shared_ptr<SubscribeStreamHandler> mSubscribeStreamHandler;
    std::shared_ptr<SubscribeToIoTCoreOperation> mSubscribeOperation;

    bool mSubscribeAsynchronously;
};
} // namespace OffboardConnectivityAwsIot
} // namespace IoTFleetWise
} // namespace Aws
