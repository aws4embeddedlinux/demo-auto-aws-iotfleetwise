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
#include "AwsIotChannel.h"
#include "Listener.h"
#include "LoggingModule.h"
#include <atomic>
#include <future>
#include <string>

#include <aws/crt/Api.h>
#include <aws/greengrass/GreengrassCoreIpcClient.h>

namespace Aws
{
namespace IoTFleetWise
{
namespace OffboardConnectivityAwsIot
{
using namespace Aws::IoTFleetWise::Platform;
using namespace Aws::Greengrass;

class IpcLifecycleHandler : public ConnectionLifecycleHandler
{
    void OnConnectCallback() override { fprintf(stdout, "Connected to Greengrass Core\n"); }

    void OnDisconnectCallback(RpcError status) override
    {
        if (!status)
        {
            fprintf(stdout, "Disconnected from Greengrass Core with error: %s\n", status.StatusToString().c_str());
        }
    }

    bool OnErrorCallback(RpcError status) override
    {
        fprintf(
            stdout,
            "Processing messages from the Greengrass Core resulted in error: %s\n",
            status.StatusToString().c_str());
        return true;
    }
};

/**
 * @brief bootstrap of the Aws Iot SDK. Only one object of this should normally exist
 * */
class AwsIotConnectivityModule : public IConnectivityModule
{
public:
    AwsIotConnectivityModule();
    ~AwsIotConnectivityModule();

    /**
     * @brief Connect to a "Thing" from the AWS IoT Core
     *
     * A thing created over the Aws CLI under IoT Core normally has a security and a collectionScheme
     * attached. The endpoint of the thing must be passed as parameter.
     * If asynchronous is false this function blocks until it succeeded or failed. Also if asynchronous is false
     * no retries are done to try to reconnected if initial connection could not be established.
     * If asynchronous is true this function returns without being connected and starts a background
     * thread that retries until it was successfully connected or aborts for some reason.
     * This function should be called only once on the object
     * @param keyFilepath File path to the private key .pem file provided during setup of the AWS
     *                      Iot Thing.
     * @param certificateFilepath File path to the certificate .crt.txt file provided during setup
     *                      of the AWS Iot Thing.
     * @param endpointUrl the endpoint URL normally in the format like
     *                          "[YOUR-THING]-ats.iot.us-west-2.amazonaws.com"
     * @param clientId the id that is used to identify this connection instance
     * @param asynchronous if true launch a background thread.
     * @return True if connecting was successful in the synchronous case or if asynchronous true if the establish
     * connection retry thread was successfully started
     */
    bool connect( const std::string &keyFilepath,
                  const std::string &certificateFilepath,
                  const std::string &endpointUrl,
                  const std::string &clientId,
                  bool asynchronous = false );

    bool disconnect();

    bool
    isAlive() const override
    {
        return mConnected;
    };

    std::shared_ptr<GreengrassCoreIpcClient>
    getConnection() const override
    {
        return mConnection;
    }

    /**
     * @brief create a new channel sharing the connection of this module
     * This call needs to be done before calling connect for all asynchronous subscribe channel
     * @param payloadManager the payload manager used by the new channel,
     *
     * @return a pointer to the newly created channel. A reference to the newly created channel is also hold inside this
     * module.
     */
    std::shared_ptr<AwsIotChannel> createNewChannel(
        const std::shared_ptr<PayloadManager> &payloadManager );

private:
    // The order is critical and ApiHandle must be the first as it setups global variables
    // like Aws::Crt::g_allocator used for example by Aws::Crt::String objects
    Aws::Crt::ApiHandle mApiHandle;
    Platform::LoggingModule mLogger;
    std::shared_ptr<GreengrassCoreIpcClient> mConnection;
    std::atomic<bool> mConnected;
    std::atomic<bool> mConnectionEstablished;
    std::vector<std::shared_ptr<AwsIotChannel>> mChannels;
    std::unique_ptr<Aws::Crt::Io::EventLoopGroup> mEventLoopGroup;
    std::unique_ptr<IpcLifecycleHandler> mLifecycleHandler;
};
} // namespace OffboardConnectivityAwsIot
} // namespace IoTFleetWise
} // namespace Aws