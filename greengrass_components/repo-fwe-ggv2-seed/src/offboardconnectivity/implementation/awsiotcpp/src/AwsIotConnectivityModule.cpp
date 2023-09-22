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

#include "AwsIotConnectivityModule.h"

#include "TraceModule.h"

#include <algorithm>

#include <aws/crt/Api.h>
#include <aws/crt/io/HostResolver.h>

#include <condition_variable>
#include <iostream>
#include <mutex>
#include <sstream>

#include "Thread.h"
#include <stdio.h>

using namespace Aws::Crt;
using namespace Aws::Greengrass;

using namespace Aws::IoTFleetWise::OffboardConnectivityAwsIot;
using namespace Aws::Crt;

AwsIotConnectivityModule::AwsIotConnectivityModule()
    : mConnected( false )
    , mConnectionEstablished( false )
{
    /* If detailed logging of the AWS IoT SDK is needed add this line:
     * mApiHandle.InitializeLogging(LogLevel::Trace,stdout);
     * */
}

/*
 * As first step to enable backend communication this code is mainly oriented on the basic_pub_sub
 * example from the Aws Iot C++ SDK
 */
bool
AwsIotConnectivityModule::connect( const std::string &keyFilepathRef,
                                   const std::string &certificateFilepathRef,
                                   const std::string &endpointUrlRef,
                                   const std::string &clientIdRef,
                                   bool asynchronous )
{
    (void)keyFilepathRef;
    (void)certificateFilepathRef;
    (void)endpointUrlRef;
    (void)clientIdRef;
    (void)asynchronous;
    mConnected = false;

    mLogger.info( "AwsIotConnectivityModule::connect", "Establishing IPC connection" );
    mEventLoopGroup = std::make_unique<Aws::Crt::Io::EventLoopGroup>(1);
    if (!*(mEventLoopGroup.get()))
    {
        fprintf(
            stderr, "Event Loop Group Creation failed with error %s\n", ErrorDebugString(mEventLoopGroup->LastError()));
        return false;
    }
    Io::DefaultHostResolver resolver(*(mEventLoopGroup.get()), 64, 30);
    Io::ClientBootstrap bootstrap(*(mEventLoopGroup.get()), resolver);
    if (!bootstrap)
    {
        fprintf(stderr, "ClientBootstrap failed with error %s\n", ErrorDebugString(bootstrap.LastError()));
        return false;
    }

    mLifecycleHandler =std::make_unique<IpcLifecycleHandler>();
    mConnection = std::make_shared<GreengrassCoreIpcClient>(bootstrap);
    auto connectionStatus = mConnection->Connect(*(mLifecycleHandler.get())).get();

    if (!connectionStatus)
    {
        fprintf(stderr, "Failed to establish connection with error %s\n", connectionStatus.StatusToString().c_str());
        return false;
    }

    mConnected = true;
    for ( auto channel : mChannels )
    {
        if ( channel->shouldSubscribeAsynchronously() )
        {
            channel->subscribe();
        }
    }

    return true;

}

std::shared_ptr<AwsIotChannel>
AwsIotConnectivityModule::createNewChannel( const std::shared_ptr<PayloadManager> &payloadManager )
{
    mChannels.emplace_back( new AwsIotChannel( this, payloadManager ) );
    return mChannels.back();
}


bool
AwsIotConnectivityModule::disconnect()
{
    return true;
}


AwsIotConnectivityModule::~AwsIotConnectivityModule()
{
    for ( auto channel : mChannels )
    {
        channel->invalidateConnection();
    }
    disconnect();
}
