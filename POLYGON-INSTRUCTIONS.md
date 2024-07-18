# Polygon's zkEVM Benchmarking
*Special thanks to Ignasi Ramos, Francesc Romero, Carlos Matallana and Héctor Masip for discussion and helping with technical issues.*

In this guide, we will set up a machine on Amazon Web Service (AWS), install Polygon's `zkevm-prover`, and produce proofs for arbitrary transactions.

Everything below has been tested on commit `d37e826111324dd5f266dc39e89fc610679f16c8` (release `v6.0.0`).

# Create an AWS Instance

The instance we used has these characteristics:

- **Machine type:** r6i.metal (128 vCPU, 1024 GiB RAM)
- **CPU Platform:** Intel(R) Xeon(R) Platinum 8375C CPU @ 2.90GHz (the CPU MUST support AVX2 instruction set)
- **Architecture:** x86_64
- **Boot disk space:** 1TB SSD
- **OS:** Ubuntu 22.04 LTS

At the time of writing, this machine costs 8.064 USD per hour. Note that there might be regions that are cheaper, or you can reduce the cost with reserved pricing.

## AWS Instructions

TODO: Stefanos


### Connect to the machine

For convenience, we would like to connect to our machine without a password

```ba
sudo visudo
# Change the line 
# %sudo   ALL=(ALL:ALL) ALL
# to
# %sudo  ALL=(ALL) NOPASSWD: ALL
```

And add your user to sudo users.

```ba
sudo adduser $USER sudo
```

### Connect to your machine using another terminal

Just add your key to the VM's `~/.ssh/authorized_keys` 
```ba
vim .ssh/authorized_keys
# Paste your public key
```


# Setup the Machine and Install Dependencies

Once you are logged in into the AWS machine, you should clone three different repositories. On your user directory (should be `ubuntu`)


```ba
# Clone zkevm-prover repository
git clone --recursive https://github.com/0xPolygonHermez/zkevm-prover.git

# Clone zkevm-testvectors repository
git clone https://github.com/0xPolygonHermez/zkevm-testvectors.git

# Clone python-cross-chain-tx-executor
git clone https://github.com/StefanosChaliasos/python-cross-chain-tx-executor.git
```

## Setting up the Prover

```ba
cd zkevm-prover
# Checkout zkevm-prover release v6.0.0
git checkout d37e826111324dd5f266dc39e89fc610679f16c8

apt install vim
# Make sure that tools/download_archive.sh has 
# `ARCHIVE_NAME="v6.0.0-rc.1-fork.9" on line 8.
vim tools/download_archive.sh


# Download necessary files (very large download ~75 GB, 
# and takes an additional 115 GB of space once extracted), 
# it's a good idea to download it now and have it running in the background:
sh ./tools/download_archive.sh


# Install dependencies
apt update
apt install build-essential libbenchmark-dev libomp-dev libgmp-dev nlohmann-json3-dev postgresql libpqxx-dev libpqxx-doc nasm libsecp256k1-dev grpc-proto libsodium-dev libprotobuf-dev libssl-dev cmake libgrpc++-dev protobuf-compiler protobuf-compiler-grpc uuid-dev
```

### Compilation

You may first need to compile the protobufs:

```ba
cd src/grpc
make
cd ../..
```

Then, run `make` to compile the main project.
```ba
make clean
make generate
# Run '-j' argument to compile the project 
# using all the threads available of the CPU... it takes a while...
make -j
```

After this, you should have a binary `zkProver` under `build` directory inside `zkevm-prover`.

# Creating the first sample proof


## Setting up Prover parameters

We will be running the prover with a sample provided by Polygon's team.

To do that, we need to modify some files.

### Modify `config_runFile_e2e.json`

Replace the content of `zkevm-prover/testvectors/config_runFile_e2e.json` file with the following:

```jso
{
    "runExecutorServer": false,
    "runExecutorClient": false,
    "runExecutorClientMultithread": false,

    "runStateDBServer": false,
    "runStateDBTest": false,

    "runAggregatorServer": true,
    "runAggregatorClient": true,
    "runAggregatorClientMock": false, 
    
    "runFileGenBatchProof": false,
    "runFileGenAggregatedProof": false,
    "runFileGenFinalProof": false,
    "runFileProcessBatch": false,
    "runFileProcessBatchMultithread": false,

    "runKeccakScriptGenerator": false,
    "runKeccakTest": false,
    "runStorageSMTest": false,
    "runBinarySMTest": false,
    "runMemAlignSMTest": false,
    "runSHA256Test": false,
    "runBlakeTest": false,

    "executeInParallel": true,
    "useMainExecGenerated": true,
    "saveRequestToFile": false,
    "saveInputToFile": true,
    "saveDbReadsToFile": false,
    "saveDbReadsToFileOnChange": false,
    "saveOutputToFile": true,
    "saveProofToFile": true,
    "saveResponseToFile": false,
    "loadDBToMemCache": true,
    "opcodeTracer": false,
    "logRemoteDbReads": false,
    "logExecutorServerResponses": false,

    "proverServerPort": 50051,
    "proverServerMockPort": 50052,
    "proverServerMockTimeout": 10000000,
    "proverClientPort": 50051,
    "proverClientHost": "127.0.0.1",

    "executorServerPort": 50071,
    "executorROMLineTraces": false,
    "executorClientPort": 50071,
    "executorClientHost": "127.0.0.1",

    "stateDBServerPort": 50061,
    "stateDBURL": "local",

    "aggregatorServerPort": 50081,
    "aggregatorClientPort": 50081,
    "aggregatorClientHost": "127.0.0.1",

    "mapConstPolsFile": false,
    "mapConstantsTreeFile": false,

    "inputFile": "testvectors/e2e/fork_9/",

    "outputPath": "runtime/output",
    "configPath": "config",

    "zkevmCmPolsAfterExecutor": "",
    "zkevmCmPols_disabled": "runtime/zkevm.commit",
    "c12aCmPols": "runtime/c12a.commit",
    "recursive1CmPols_disabled": "runtime/recursive1.commit",
    "recursive2CmPols_disabled": "runtime/recursive2.commit",
    "recursivefCmPols_disabled": "runtime/recursivef.commit",
    "finalCmPols_disabled": "runtime/final.commit",

    "publicsOutput": "public.json",
    "proofFile": "proof.json",

    "databaseURL": "local",
    "databaseURL_disabled": "postgresql://statedb:statedb@127.0.0.1:5432/testdb",
    "dbNodesTableName": "state.nodes",
    "dbProgramTableName": "state.program",
    "dbAsyncWrite": false,
    "cleanerPollingPeriod": 600,
    "requestsPersistence": 3600,
    "maxExecutorThreads": 20,
    "maxProverThreads": 8,
    "maxStateDBThreads": 8,
    "aggregatorClientMaxStreams": 1
}
```

Save the changes.

### Modify `aggregator_service.cpp`

Search for `aggregator_service.cpp` file inside `zkevm-prover` (should be on `zkevm-prover/test/service/aggregator`) And replace the content of this file with the following:

```c++
#include "config.hpp"
#include "aggregator_service.hpp"
#include "input.hpp"
#include "proof_fflonk.hpp"
#include "definitions.hpp"
#include <grpcpp/grpcpp.h>
#include <chrono>
#include <iostream>
#include <fstream>

using grpc::Server;
using grpc::ServerBuilder;
using grpc::ServerContext;
using grpc::Status;

#define AGGREGATOR_SERVER_NUMBER_OF_LOOPS 1

#define AGGREGATOR_SERVER_RETRY_SLEEP 10
#define AGGREGATOR_SERVER_NUMBER_OF_GET_PROOF_RETRIES 600  // 600 retries every 10 seconds = 6000 seconds = 100 minutes

::grpc::Status AggregatorServiceImpl::Channel(::grpc::ServerContext* context, ::grpc::ServerReaderWriter< ::aggregator::v1::AggregatorMessage, ::aggregator::v1::ProverMessage>* stream)
{
#ifdef LOG_SERVICE
    cout << "AggregatorServiceImpl::Channel() stream starts" << endl;
#endif
    aggregator::v1::AggregatorMessage aggregatorMessage;
    aggregator::v1::ProverMessage proverMessage;
    aggregator::v1::Result result;
    string uuid;
    ::grpc::Status grpcStatus;
    string requestID;
    string proof;

    const string inputFile0  = "testvectors/e2e/" + string(PROVER_FORK_NAMESPACE_STRING) + "/input_executor_0.json";
    const string outputFile0 = "testvectors/aggregatedProof/recursive1.zkin.proof_0.json";

    const string inputFile1  = "testvectors/e2e/" + string(PROVER_FORK_NAMESPACE_STRING) + "/input_executor_1.json";
    const string outputFile1 = "testvectors/aggregatedProof/recursive1.zkin.proof_1.json";

    const string inputFile01a = outputFile0;
    const string inputFile01b = outputFile1;
    const string outputFile01 = "testvectors/finalProof/recursive2.zkin.proof_01.json";

    const string inputFile2  = "testvectors/e2e/" + string(PROVER_FORK_NAMESPACE_STRING) + "/input_executor_2.json";
    const string outputFile2 = "testvectors/aggregatedProof/recursive1.zkin.proof_2.json";
    
    const string inputFile3  = "testvectors/e2e/" + string(PROVER_FORK_NAMESPACE_STRING) + "/input_executor_3.json";
    const string outputFile3 = "testvectors/aggregatedProof/recursive1.zkin.proof_3.json";

    const string inputFile23a = outputFile2;
    const string inputFile23b = outputFile3;
    const string outputFile23 = "testvectors/finalProof/recursive2.zkin.proof_23.json";

    const string inputFile03a = outputFile01;
    const string inputFile03b = outputFile23;
    const string outputFile03 = "testvectors/finalProof/recursive2.zkin.proof_03.json";

    string inputFileFinal  = outputFile03;
    const string outputFileFinal = "testvectors/finalProof/proof.json";

    std::ofstream outputFile("benchmarks.csv", std::ios::app | std::ios::out);


    // Get status
    grpcStatus = GetStatus(context, stream);
    if (grpcStatus.error_code() != Status::OK.error_code())
    {
        return grpcStatus;
    }

    // Cancel an invalid request ID and check result
    grpcStatus = Cancel(context, stream, "invalid_id", result);
    if (grpcStatus.error_code() != Status::OK.error_code())
    {
        return grpcStatus;
    }
    if (result != aggregator::v1::Result::RESULT_ERROR)
    {
        cerr << "Error: AggregatorServiceImpl::Channel() got cancel result=" << result << " instead of RESULT_CANCEL_ERROR" << endl;
        return Status::CANCELLED;
    }

    for ( uint64_t loop=0; loop<AGGREGATOR_SERVER_NUMBER_OF_LOOPS; loop++ )
    {
        // Generate batch proof 0
        // Start timer
        auto start = std::chrono::high_resolution_clock::now();
        grpcStatus = GenAndGetBatchProof(context, stream, inputFile0, outputFile0);
        if (grpcStatus.error_code() != Status::OK.error_code())
        {
            return grpcStatus;
        }
        cout << "AggregatorServiceImpl::Channel() called GenAndGetBatchProof(" << inputFile0 << ", " << outputFile0 << ")" << endl;
        // Stop timer
        auto stop = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(stop - start);
        // Create an output file stream (ofstream)
        // Check if the file is open successfully
        if (outputFile.is_open()) {
            // Write the elapsed time to the file
            outputFile << duration.count() << ", ";
        } else {
            std::cout << "Error opening file!" << std::endl;
        }



        // // Generate batch proof 1
        // start = std::chrono::high_resolution_clock::now();
        // grpcStatus = GenAndGetBatchProof(context, stream, inputFile1, outputFile1);
        // if (grpcStatus.error_code() != Status::OK.error_code())
        // {
        //     return grpcStatus;
        // }
        // cout << "AggregatorServiceImpl::Channel() called GenAndGetBatchProof(" << inputFile1 << ", " << outputFile1 << ")" << endl;
        // stop = std::chrono::high_resolution_clock::now();
        // duration = std::chrono::duration_cast<std::chrono::milliseconds>(stop - start);

        // // Check if the file is open successfully
        // if (outputFile.is_open()) {
        //     // Write the elapsed time to the file
        //     outputFile << duration.count() << ", ";
        // } else {
        //     std::cout << "Error opening file!" << std::endl;
        // }


        // // Generate aggregated proof 01
        // start = std::chrono::high_resolution_clock::now();
        // grpcStatus = GenAndGetAggregatedProof(context, stream, inputFile01a, inputFile01b, outputFile01);
        // if (grpcStatus.error_code() != Status::OK.error_code())
        // {
        //     return grpcStatus;
        // }
        // cout << "AggregatorServiceImpl::Channel() called GenAndGetAggregatedProof(" << inputFile01a << ", " << inputFile01b << ", " << outputFile01 << ")" << endl;
        // stop = std::chrono::high_resolution_clock::now();
        // duration = std::chrono::duration_cast<std::chrono::milliseconds>(stop - start);

        // // Check if the file is open successfully
        // if (outputFile.is_open()) {
        //     // Write the elapsed time to the file
        //     outputFile << duration.count() << ", ";
        // } else {
        //     std::cout << "Error opening file!" << std::endl;
        // }

        // // Generate batch proof 2
        // start = std::chrono::high_resolution_clock::now();
        // grpcStatus = GenAndGetBatchProof(context, stream, inputFile2, outputFile2);
        // if (grpcStatus.error_code() != Status::OK.error_code())
        // {
        //     return grpcStatus;
        // }
        // cout << "AggregatorServiceImpl::Channel() called GenAndGetBatchProof(" << inputFile2 << ", " << outputFile2 << ")" << endl;
        // stop = std::chrono::high_resolution_clock::now();
        // duration = std::chrono::duration_cast<std::chrono::milliseconds>(stop - start);

        // // Check if the file is open successfully
        // if (outputFile.is_open()) {
        //     // Write the elapsed time to the file
        //     outputFile << duration.count() << ", ";
        // } else {
        //     std::cout << "Error opening file!" << std::endl;
        // }


        // // Generate batch proof 3
        // start = std::chrono::high_resolution_clock::now();
        // grpcStatus = GenAndGetBatchProof(context, stream, inputFile3, outputFile3);
        // if (grpcStatus.error_code() != Status::OK.error_code())
        // {
        //     return grpcStatus;
        // }
        // cout << "AggregatorServiceImpl::Channel() called GenAndGetBatchProof(" << inputFile3 << ", " << outputFile3 << ")" << endl;
        // stop = std::chrono::high_resolution_clock::now();
        // duration = std::chrono::duration_cast<std::chrono::milliseconds>(stop - start);

        // // Check if the file is open successfully
        // if (outputFile.is_open()) {
        //     // Write the elapsed time to the file
        //     outputFile << duration.count() << ", ";
        // } else {
        //     std::cout << "Error opening file!" << std::endl;
        // }


        // // Generate aggregated proof 23
        // start = std::chrono::high_resolution_clock::now();
        // grpcStatus = GenAndGetAggregatedProof(context, stream, inputFile23a, inputFile23b, outputFile23);
        // if (grpcStatus.error_code() != Status::OK.error_code())
        // {
        //     return grpcStatus;
        // }
        // cout << "AggregatorServiceImpl::Channel() called GenAndGetAggregatedProof(" << inputFile23a << ", " << inputFile23b << ", " << outputFile23 << ")" << endl;
        // stop = std::chrono::high_resolution_clock::now();
        // duration = std::chrono::duration_cast<std::chrono::milliseconds>(stop - start);

        // // Check if the file is open successfully
        // if (outputFile.is_open()) {
        //     // Write the elapsed time to the file
        //     outputFile << duration.count() << ", ";
        // } else {
        //     std::cout << "Error opening file!" << std::endl;
        // }

        // // Generate aggregated proof 0123
        // start = std::chrono::high_resolution_clock::now();
        // grpcStatus = GenAndGetAggregatedProof(context, stream, inputFile03a, inputFile03b, outputFile03);
        // if (grpcStatus.error_code() != Status::OK.error_code())
        // {
        //     return grpcStatus;
        // }
        // cout << "AggregatorServiceImpl::Channel() called GenAndGetAggregatedProof(" << inputFile03a << ", " << inputFile03b << ", " << outputFile03 << ")" << endl;
        // stop = std::chrono::high_resolution_clock::now();
        // duration = std::chrono::duration_cast<std::chrono::milliseconds>(stop - start);

        // // Check if the file is open successfully
        // if (outputFile.is_open()) {
        //     // Write the elapsed time to the file
        //     outputFile << duration.count() << ", ";
        // } else {
        //     std::cout << "Error opening file!" << std::endl;
        // }


        // Generate final proof
        start = std::chrono::high_resolution_clock::now();
        inputFileFinal = outputFile01;
        grpcStatus = GenAndGetFinalProof(context, stream, inputFileFinal, outputFileFinal);
        if (grpcStatus.error_code() != Status::OK.error_code())
        {
            return grpcStatus;
        }
        cout << "AggregatorServiceImpl::Channel() called GenAndGetFinalProof(" << inputFileFinal << ", " << outputFileFinal << ")" << endl;
        stop = std::chrono::high_resolution_clock::now();
        duration = std::chrono::duration_cast<std::chrono::milliseconds>(stop - start);

        // Check if the file is open successfully
        if (outputFile.is_open()) {
            // Write the elapsed time to the file
            outputFile << duration.count() << std::endl;
            // Close the file
            outputFile.close();
        } else {
            std::cout << "Error opening file!" << std::endl;
        }
    }

    return Status::OK;
}

::grpc::Status AggregatorServiceImpl::GetStatus(::grpc::ServerContext* context, ::grpc::ServerReaderWriter< ::aggregator::v1::AggregatorMessage, ::aggregator::v1::ProverMessage>* stream)
{
    aggregator::v1::AggregatorMessage aggregatorMessage;
    aggregator::v1::ProverMessage proverMessage;
    bool bResult;
    string uuid;

    // Send a get status request message
    aggregatorMessage.Clear();
    aggregator::v1::GetStatusRequest * pGetStatusRequest = new aggregator::v1::GetStatusRequest();
    zkassertpermanent(pGetStatusRequest != NULL);
    aggregatorMessage.set_allocated_get_status_request(pGetStatusRequest);
    messageId++;
    aggregatorMessage.set_id(to_string(messageId));
    bResult = stream->Write(aggregatorMessage);
    if (!bResult)
    {
        cerr << "Error: AggregatorServiceImpl::GetStatus() failed calling stream->Write(aggregatorMessage)" << endl;
        return Status::CANCELLED;
    }

    // Receive the corresponding get status response message
    proverMessage.Clear();
    bResult = stream->Read(&proverMessage);
    if (!bResult)
    {
        cerr << "Error: AggregatorServiceImpl::GetStatus() failed calling stream->Read(proverMessage)" << endl;
        return Status::CANCELLED;
    }
    
    // Check type
    if (proverMessage.response_case() != aggregator::v1::ProverMessage::ResponseCase::kGetStatusResponse)
    {
        cerr << "Error: AggregatorServiceImpl::GetStatus() got proverMessage.response_case=" << proverMessage.response_case() << " instead of GET_STATUS_RESPONSE" << endl;
        return Status::CANCELLED;
    }

    // Check id
    if (proverMessage.id() != aggregatorMessage.id())
    {
        cerr << "Error: AggregatorServiceImpl::GetStatus() got proverMessage.id=" << proverMessage.id() << " instead of aggregatorMessage.id=" << aggregatorMessage.id() << endl;
        return Status::CANCELLED;
    }

    return Status::OK;
}

::grpc::Status AggregatorServiceImpl::Cancel(::grpc::ServerContext* context, ::grpc::ServerReaderWriter< ::aggregator::v1::AggregatorMessage, ::aggregator::v1::ProverMessage>* stream, const string &requestID, aggregator::v1::Result &result)
{
    aggregator::v1::AggregatorMessage aggregatorMessage;
    aggregator::v1::ProverMessage proverMessage;
    bool bResult;
    string uuid;

    // Send a cancel request message
    aggregatorMessage.Clear();
    messageId++;
    aggregatorMessage.set_id(to_string(messageId));
    aggregator::v1::CancelRequest * pCancelRequest = new aggregator::v1::CancelRequest();
    zkassertpermanent(pCancelRequest != NULL);
    pCancelRequest->set_id(requestID);
    aggregatorMessage.set_allocated_cancel_request(pCancelRequest);
    bResult = stream->Write(aggregatorMessage);
    if (!bResult)
    {
        cerr << "Error: AggregatorServiceImpl::Channel() failed calling stream->Write(aggregatorMessage)" << endl;
        return Status::CANCELLED;
    }

    // Receive the corresponding cancel response message
    proverMessage.Clear();
    bResult = stream->Read(&proverMessage);
    if (!bResult)
    {
        cerr << "Error: AggregatorServiceImpl::Channel() failed calling stream->Read(proverMessage)" << endl;
        return Status::CANCELLED;
    }
    
    // Check type
    if (proverMessage.response_case() != aggregator::v1::ProverMessage::ResponseCase::kCancelResponse)
    {
        cerr << "Error: AggregatorServiceImpl::Channel() got proverMessage.response_case=" << proverMessage.response_case() << " instead of CANCEL_RESPONSE" << endl;
        return Status::CANCELLED;
    }

    // Check id
    if (proverMessage.id() != aggregatorMessage.id())
    {
        cerr << "Error: AggregatorServiceImpl::Channel() got proverMessage.id=" << proverMessage.id() << " instead of aggregatorMessage.id=" << aggregatorMessage.id() << endl;
        return Status::CANCELLED;
    }

    // Check cancel result
    result = proverMessage.cancel_response().result();

    return Status::OK;
}

::grpc::Status AggregatorServiceImpl::GenBatchProof(::grpc::ServerContext* context, ::grpc::ServerReaderWriter< ::aggregator::v1::AggregatorMessage, ::aggregator::v1::ProverMessage>* stream, const string &inputFile, string &requestID)
{
    aggregator::v1::AggregatorMessage aggregatorMessage;
    aggregator::v1::ProverMessage proverMessage;
    bool bResult;
    string uuid;

    if (inputFile.size() == 0)
    {
        cerr << "Error: AggregatorServiceImpl::GenBatchProof() found inputFile empty" << endl;
        exitProcess();
    }

    aggregator::v1::InputProver *pInputProver = new aggregator::v1::InputProver();
    zkassertpermanent(pInputProver != NULL);
    Input input(fr);
    json inputJson;
    file2json(inputFile, inputJson);
    zkresult zkResult = input.load(inputJson);
    if (zkResult != ZKR_SUCCESS)
    {
        cerr << "Error: AggregatorServiceImpl::GenBatchProof() failed calling input.load() zkResult=" << zkResult << "=" << zkresult2string(zkResult) << endl;
        exitProcess();
    }

    // Parse public inputs
    aggregator::v1::PublicInputs * pPublicInputs = new aggregator::v1::PublicInputs();
    pPublicInputs->set_old_state_root(scalar2ba(input.publicInputsExtended.publicInputs.oldStateRoot));
    pPublicInputs->set_old_acc_input_hash(scalar2ba(input.publicInputsExtended.publicInputs.oldAccInputHash));
    pPublicInputs->set_old_batch_num(input.publicInputsExtended.publicInputs.oldBatchNum);
    pPublicInputs->set_chain_id(input.publicInputsExtended.publicInputs.chainID);
    pPublicInputs->set_fork_id(input.publicInputsExtended.publicInputs.forkID);
    pPublicInputs->set_batch_l2_data(input.publicInputsExtended.publicInputs.batchL2Data);
    pPublicInputs->set_l1_info_root(scalar2ba(input.publicInputsExtended.publicInputs.l1InfoRoot));
    pPublicInputs->set_timestamp_limit(input.publicInputsExtended.publicInputs.timestampLimit);
    pPublicInputs->set_forced_blockhash_l1(scalar2ba(input.publicInputsExtended.publicInputs.forcedBlockHashL1));
    pPublicInputs->set_sequencer_addr(Add0xIfMissing(input.publicInputsExtended.publicInputs.sequencerAddr.get_str(16)));
    pPublicInputs->set_aggregator_addr(Add0xIfMissing(input.publicInputsExtended.publicInputs.aggregatorAddress.get_str(16)));
    pInputProver->set_allocated_public_inputs(pPublicInputs);

    // Parse keys map
    DatabaseMap::MTMap::const_iterator it;
    for (it=input.db.begin(); it!=input.db.end(); it++)
    {
        string key = NormalizeToNFormat(it->first, 64);
        string value;
        vector<Goldilocks::Element> dbValue = it->second;
        for (uint64_t i=0; i<dbValue.size(); i++)
        {
            value += NormalizeToNFormat(fr.toString(dbValue[i], 16), 16);
        }
        (*pInputProver->mutable_db())[key] = value;
    }

    // Parse contracts data
    DatabaseMap::ProgramMap::const_iterator itc;
    for (itc=input.contractsBytecode.begin(); itc!=input.contractsBytecode.end(); itc++)
    {
        string key = NormalizeToNFormat(itc->first, 64);
        string value;
        vector<uint8_t> contractValue = itc->second;
        for (uint64_t i=0; i<contractValue.size(); i++)
        {
            value += byte2string(contractValue[i]);
        }
        (*pInputProver->mutable_contracts_bytecode())[key] = value;
    }

    unordered_map<uint64_t, L1Data>::const_iterator itL1Data;
    for (itL1Data = input.l1InfoTreeData.begin(); itL1Data != input.l1InfoTreeData.end(); itL1Data++)
    {
        aggregator::v1::L1Data l1Data;
        l1Data.set_global_exit_root(string2ba(itL1Data->second.globalExitRoot.get_str(16)));
        l1Data.set_blockhash_l1(string2ba(itL1Data->second.blockHashL1.get_str(16)));
        l1Data.set_min_timestamp(itL1Data->second.minTimestamp);
        for (uint64_t i=0; i<itL1Data->second.smtProof.size(); i++)
        {
            l1Data.add_smt_proof(string2ba(itL1Data->second.smtProof[i].get_str(16)));
        }
        (*pInputProver->mutable_public_inputs()->mutable_l1_info_tree_data())[itL1Data->first] = l1Data;
    }

    // Allocate the gen batch request
    aggregator::v1::GenBatchProofRequest *pGenBatchProofRequest = new aggregator::v1::GenBatchProofRequest();
    zkassertpermanent(pGenBatchProofRequest != NULL );
    pGenBatchProofRequest->set_allocated_input(pInputProver);

    // Send the gen proof request
    aggregatorMessage.Clear();
    messageId++;
    aggregatorMessage.set_id(to_string(messageId));
    aggregatorMessage.set_allocated_gen_batch_proof_request(pGenBatchProofRequest);
    bResult = stream->Write(aggregatorMessage);
    if (!bResult)
    {
        cerr << "Error: AggregatorServiceImpl::Channel() failed calling stream->Write(aggregatorMessage)" << endl;
        return Status::CANCELLED;
    }

    // Receive the corresponding get proof response message
    proverMessage.Clear();
    bResult = stream->Read(&proverMessage);
    if (!bResult)
    {
        cerr << "Error: AggregatorServiceImpl::Channel() failed calling stream->Read(proverMessage)" << endl;
        return Status::CANCELLED;
    }
    
    // Check type
    if (proverMessage.response_case() != aggregator::v1::ProverMessage::ResponseCase::kGenBatchProofResponse)
    {
        cerr << "Error: AggregatorServiceImpl::Channel() got proverMessage.response_case=" << proverMessage.response_case() << " instead of GEN_BATCH_PROOF_RESPONSE" << endl;
        return Status::CANCELLED;
    }

    // Check id
    if (proverMessage.id() != aggregatorMessage.id())
    {
        cerr << "Error: AggregatorServiceImpl::Channel() got proverMessage.id=" << proverMessage.id() << " instead of aggregatorMessage.id=" << aggregatorMessage.id() << endl;
        return Status::CANCELLED;
    }

    requestID = proverMessage.gen_batch_proof_response().id();

    return Status::OK;
}

::grpc::Status AggregatorServiceImpl::GenAggregatedProof(::grpc::ServerContext* context, ::grpc::ServerReaderWriter< ::aggregator::v1::AggregatorMessage, ::aggregator::v1::ProverMessage>* stream, const string &inputFileA, const string &inputFileB, string &requestID)
{
    aggregator::v1::AggregatorMessage aggregatorMessage;
    aggregator::v1::ProverMessage proverMessage;
    bool bResult;
    string uuid;
    string inputFileAContent;
    string inputFileBContent;

    if (inputFileA.size() == 0)
    {
        cerr << "Error: AggregatorServiceImpl::GenAggregatedProof() found inputFileA empty" << endl;
        exitProcess();
    }
    file2string(inputFileA, inputFileAContent);

    if (inputFileB.size() == 0)
    {
        cerr << "Error: AggregatorServiceImpl::GenAggregatedProof() found inputFileB empty" << endl;
        exitProcess();
    }
    file2string(inputFileB, inputFileBContent);

    // Allocate the aggregated batch request
    aggregator::v1::GenAggregatedProofRequest *pGenAggregatedProofRequest = new aggregator::v1::GenAggregatedProofRequest();
    zkassertpermanent(pGenAggregatedProofRequest != NULL );
    pGenAggregatedProofRequest->set_recursive_proof_1(inputFileAContent);
    pGenAggregatedProofRequest->set_recursive_proof_2(inputFileBContent);

    // Send the gen proof request
    aggregatorMessage.Clear();
    messageId++;
    aggregatorMessage.set_id(to_string(messageId));
    aggregatorMessage.set_allocated_gen_aggregated_proof_request(pGenAggregatedProofRequest);
    bResult = stream->Write(aggregatorMessage);
    if (!bResult)
    {
        cerr << "Error: AggregatorServiceImpl::GenAggregatedProof() failed calling stream->Write(aggregatorMessage)" << endl;
        return Status::CANCELLED;
    }

    // Receive the corresponding get proof response message
    proverMessage.Clear();
    bResult = stream->Read(&proverMessage);
    if (!bResult)
    {
        cerr << "Error: AggregatorServiceImpl::GenAggregatedProof() failed calling stream->Read(proverMessage)" << endl;
        return Status::CANCELLED;
    }
    
    // Check type
    if (proverMessage.response_case() != aggregator::v1::ProverMessage::ResponseCase::kGenAggregatedProofResponse)
    {
        cerr << "Error: AggregatorServiceImpl::GenAggregatedProof() got proverMessage.response_case=" << proverMessage.response_case() << " instead of GEN_AGGREGATED_PROOF_RESPONSE" << endl;
        return Status::CANCELLED;
    }

    // Check id
    if (proverMessage.id() != aggregatorMessage.id())
    {
        cerr << "Error: AggregatorServiceImpl::GenAggregatedProof() got proverMessage.id=" << proverMessage.id() << " instead of aggregatorMessage.id=" << aggregatorMessage.id() << endl;
        return Status::CANCELLED;
    }

    requestID = proverMessage.gen_aggregated_proof_response().id();

    return Status::OK;
}

::grpc::Status AggregatorServiceImpl::GenFinalProof(::grpc::ServerContext* context, ::grpc::ServerReaderWriter< ::aggregator::v1::AggregatorMessage, ::aggregator::v1::ProverMessage>* stream, const string &inputFile, string &requestID)
{
    aggregator::v1::AggregatorMessage aggregatorMessage;
    aggregator::v1::ProverMessage proverMessage;
    bool bResult;
    string uuid;
    string inputFileContent;

    if (inputFile.size() == 0)
    {
        cerr << "Error: AggregatorServiceImpl::GenFinalProof() found inputFile empty" << endl;
        exitProcess();
    }
    file2string(inputFile, inputFileContent);

    // Allocate the final batch request
    aggregator::v1::GenFinalProofRequest *pGenFinalProofRequest = new aggregator::v1::GenFinalProofRequest();
    zkassertpermanent(pGenFinalProofRequest != NULL );
    pGenFinalProofRequest->set_recursive_proof(inputFileContent);

    // Send the gen proof request
    aggregatorMessage.Clear();
    messageId++;
    aggregatorMessage.set_id(to_string(messageId));
    aggregatorMessage.set_allocated_gen_final_proof_request(pGenFinalProofRequest);
    bResult = stream->Write(aggregatorMessage);
    if (!bResult)
    {
        cerr << "Error: AggregatorServiceImpl::GenFinalProof() failed calling stream->Write(aggregatorMessage)" << endl;
        return Status::CANCELLED;
    }

    // Receive the corresponding get proof response message
    proverMessage.Clear();
    bResult = stream->Read(&proverMessage);
    if (!bResult)
    {
        cerr << "Error: AggregatorServiceImpl::GenFinalProof() failed calling stream->Read(proverMessage)" << endl;
        return Status::CANCELLED;
    }
    
    // Check type
    if (proverMessage.response_case() != aggregator::v1::ProverMessage::ResponseCase::kGenFinalProofResponse)
    {
        cerr << "Error: AggregatorServiceImpl::GenFinalProof() got proverMessage.response_case=" << proverMessage.response_case() << " instead of GEN_AGGREGATED_PROOF_RESPONSE" << endl;
        return Status::CANCELLED;
    }

    // Check id
    if (proverMessage.id() != aggregatorMessage.id())
    {
        cerr << "Error: AggregatorServiceImpl::GenFinalProof() got proverMessage.id=" << proverMessage.id() << " instead of aggregatorMessage.id=" << aggregatorMessage.id() << endl;
        return Status::CANCELLED;
    }

    requestID = proverMessage.gen_final_proof_response().id();

    return Status::OK;
}

::grpc::Status AggregatorServiceImpl::GetProof(::grpc::ServerContext* context, ::grpc::ServerReaderWriter< ::aggregator::v1::AggregatorMessage, ::aggregator::v1::ProverMessage>* stream, const string &requestID, aggregator::v1::GetProofResponse_Result &result, string &proof)
{
    aggregator::v1::AggregatorMessage aggregatorMessage;
    aggregator::v1::ProverMessage proverMessage;
    bool bResult;

    // Send a get proof request message
    aggregatorMessage.Clear();
    messageId++;
    aggregatorMessage.set_id(to_string(messageId));
    aggregator::v1::GetProofRequest * pGetProofRequest = new aggregator::v1::GetProofRequest();
    zkassertpermanent(pGetProofRequest != NULL);
    pGetProofRequest->set_id(requestID);
    aggregatorMessage.set_allocated_get_proof_request(pGetProofRequest);
    bResult = stream->Write(aggregatorMessage);
    if (!bResult)
    {
        cerr << "Error: AggregatorServiceImpl::Channel() failed calling stream->Write(aggregatorMessage)" << endl;
        return Status::CANCELLED;
    }

    // Receive the corresponding get proof response message
    proverMessage.Clear();
    bResult = stream->Read(&proverMessage);
    if (!bResult)
    {
        cerr << "Error: AggregatorServiceImpl::Channel() failed calling stream->Read(proverMessage)" << endl;
        return Status::CANCELLED;
    }
    
    // Check type
    if (proverMessage.response_case() != aggregator::v1::ProverMessage::ResponseCase::kGetProofResponse)
    {
        cerr << "Error: AggregatorServiceImpl::Channel() got proverMessage.response_case=" << proverMessage.response_case() << " instead of GET_PROOF_RESPONSE" << endl;
        return Status::CANCELLED;
    }

    // Check id
    if (proverMessage.id() != aggregatorMessage.id())
    {
        cerr << "Error: AggregatorServiceImpl::Channel() got proverMessage.id=" << proverMessage.id() << " instead of aggregatorMessage.id=" << aggregatorMessage.id() << endl;
        return Status::CANCELLED;
    }

    // Copy get proof result
    result = proverMessage.get_proof_response().result();
    if ( proverMessage.get_proof_response().has_final_proof() )
    {
        proof = proverMessage.get_proof_response().final_proof().proof();
    }
    else
    {
        proof = proverMessage.get_proof_response().recursive_proof();
    }

    return Status::OK;
}

::grpc::Status AggregatorServiceImpl::GenAndGetBatchProof(::grpc::ServerContext* context, ::grpc::ServerReaderWriter< ::aggregator::v1::AggregatorMessage, ::aggregator::v1::ProverMessage>* stream, const string & inputFile, const string &outputFile)
{
    ::grpc::Status grpcStatus;
    string requestID;
    string proof;
    uint64_t i;

    // Generate batch proof 0
    grpcStatus = GenBatchProof(context, stream, inputFile, requestID);
    if (grpcStatus.error_code() != Status::OK.error_code())
    {
        return grpcStatus;
    }
    cout << "AggregatorServiceImpl::GenAndGetBatchProof() called GenBatchProof() and got requestID=" << requestID << endl;

    // Get batch proof 0
    for (i=0; i<AGGREGATOR_SERVER_NUMBER_OF_GET_PROOF_RETRIES; i++)
    {
        sleep(AGGREGATOR_SERVER_RETRY_SLEEP);

        aggregator::v1::GetProofResponse_Result getProofResponseResult;
        grpcStatus = GetProof(context, stream, requestID, getProofResponseResult, proof);        
        if (grpcStatus.error_code() != Status::OK.error_code())
        {
            return grpcStatus;
        }

        if (getProofResponseResult == aggregator::v1::GetProofResponse_Result_RESULT_COMPLETED_OK)
        {
            break;
        }        
        if (getProofResponseResult == aggregator::v1::GetProofResponse_Result_RESULT_PENDING)
        {
            continue;
        }
        cerr << "Error: AggregatorServiceImpl::GenAndGetBatchProof() got getProofResponseResult=" << getProofResponseResult << " instead of RESULT_PENDING or RESULT_COMPLETED_OK" << endl;
        return Status::CANCELLED;
    }
    if (i == AGGREGATOR_SERVER_NUMBER_OF_GET_PROOF_RETRIES)
    {
        cerr << "Error: AggregatorServiceImpl::GenAndGetBatchProof() timed out waiting for batch proof" << endl;
        return Status::CANCELLED;
    }
    if (proof.size() == 0)
    {
        cerr << "Error: AggregatorServiceImpl::GenAndGetBatchProof() got an empty batch proof" << endl;
        return Status::CANCELLED;
    }
    string2file(proof, outputFile);

    return Status::OK;
}

::grpc::Status AggregatorServiceImpl::GenAndGetAggregatedProof(::grpc::ServerContext* context, ::grpc::ServerReaderWriter< ::aggregator::v1::AggregatorMessage, ::aggregator::v1::ProverMessage>* stream, const string & inputFileA, const string & inputFileB, const string &outputFile)
{
    ::grpc::Status grpcStatus;
    string requestID;
    string proof;
    uint64_t i;

    // Generate batch proof 0
    grpcStatus = GenAggregatedProof(context, stream, inputFileA, inputFileB, requestID);
    if (grpcStatus.error_code() != Status::OK.error_code())
    {
        return grpcStatus;
    }
    cout << "AggregatorServiceImpl::GenAndGetAggregatedProof() called GenAggregatedProof() and got requestID=" << requestID << endl;

    // Get batch proof 0
    for (i=0; i<AGGREGATOR_SERVER_NUMBER_OF_GET_PROOF_RETRIES; i++)
    {
        sleep(AGGREGATOR_SERVER_RETRY_SLEEP);

        aggregator::v1::GetProofResponse_Result getProofResponseResult;
        grpcStatus = GetProof(context, stream, requestID, getProofResponseResult, proof);        
        if (grpcStatus.error_code() != Status::OK.error_code())
        {
            return grpcStatus;
        }

        if (getProofResponseResult == aggregator::v1::GetProofResponse_Result_RESULT_COMPLETED_OK)
        {
            break;
        }        
        if (getProofResponseResult == aggregator::v1::GetProofResponse_Result_RESULT_PENDING)
        {
            continue;
        }
        cerr << "Error: AggregatorServiceImpl::GenAndGetAggregatedProof() got getProofResponseResult=" << getProofResponseResult << " instead of RESULT_PENDING or RESULT_COMPLETED_OK" << endl;
        return Status::CANCELLED;
    }
    if (i == AGGREGATOR_SERVER_NUMBER_OF_GET_PROOF_RETRIES)
    {
        cerr << "Error: AggregatorServiceImpl::GenAndGetAggregatedProof() timed out waiting for batch proof" << endl;
        return Status::CANCELLED;
    }
    if (proof.size() == 0)
    {
        cerr << "Error: AggregatorServiceImpl::GenAndGetAggregatedProof() got an empty batch proof" << endl;
        return Status::CANCELLED;
    }
    string2file(proof, outputFile);

    return Status::OK;
}

::grpc::Status AggregatorServiceImpl::GenAndGetFinalProof(::grpc::ServerContext* context, ::grpc::ServerReaderWriter< ::aggregator::v1::AggregatorMessage, ::aggregator::v1::ProverMessage>* stream, const string & inputFile, const string &outputFile)
{
    ::grpc::Status grpcStatus;
    string requestID;
    string proof;
    uint64_t i;

    // Generate batch proof 0
    grpcStatus = GenFinalProof(context, stream, inputFile, requestID);
    if (grpcStatus.error_code() != Status::OK.error_code())
    {
        return grpcStatus;
    }
    cout << "AggregatorServiceImpl::GenAndGetFinalProof() called GenFinalProof() and got requestID=" << requestID << endl;

    // Get batch proof 0
    for (i=0; i<AGGREGATOR_SERVER_NUMBER_OF_GET_PROOF_RETRIES; i++)
    {
        sleep(AGGREGATOR_SERVER_RETRY_SLEEP);

        aggregator::v1::GetProofResponse_Result getProofResponseResult;
        grpcStatus = GetProof(context, stream, requestID, getProofResponseResult, proof);        
        if (grpcStatus.error_code() != Status::OK.error_code())
        {
            return grpcStatus;
        }

        if (getProofResponseResult == aggregator::v1::GetProofResponse_Result_RESULT_COMPLETED_OK)
        {
            break;
        }        
        if (getProofResponseResult == aggregator::v1::GetProofResponse_Result_RESULT_PENDING)
        {
            continue;
        }
        cerr << "Error: AggregatorServiceImpl::GenAndGetFinalProof() got getProofResponseResult=" << getProofResponseResult << " instead of RESULT_PENDING or RESULT_COMPLETED_OK" << endl;
        return Status::CANCELLED;
    }
    if (i == AGGREGATOR_SERVER_NUMBER_OF_GET_PROOF_RETRIES)
    {
        cerr << "Error: AggregatorServiceImpl::GenAndGetFinalProof() timed out waiting for batch proof" << endl;
        return Status::CANCELLED;
    }
    if (proof.size() == 0)
    {
        cerr << "Error: AggregatorServiceImpl::GenAndGetFinalProof() got an empty batch proof" << endl;
        return Status::CANCELLED;
    }
    string2file(proof, outputFile);

    return Status::OK;
}

::grpc::Status AggregatorServiceImpl::ChannelOld(::grpc::ServerContext* context, ::grpc::ServerReaderWriter< ::aggregator::v1::AggregatorMessage, ::aggregator::v1::ProverMessage>* stream)
{
#ifdef LOG_SERVICE
    cout << "AggregatorServiceImpl::Channel() stream starts" << endl;
#endif
    aggregator::v1::AggregatorMessage aggregatorMessage;
    aggregator::v1::ProverMessage proverMessage;
    bool bResult;
    string uuid;

    //while (true)
    {
        // CALL GET STATUS

        // Send a get status request message
        aggregatorMessage.Clear();
        aggregator::v1::GetStatusRequest * pGetStatusRequest = new aggregator::v1::GetStatusRequest();
        zkassertpermanent(pGetStatusRequest != NULL);
        aggregatorMessage.set_allocated_get_status_request(pGetStatusRequest);
        messageId++;
        aggregatorMessage.set_id(to_string(messageId));
        bResult = stream->Write(aggregatorMessage);
        if (!bResult)
        {
            cerr << "Error: AggregatorServiceImpl::Channel() failed calling stream->Write(aggregatorMessage)" << endl;
            return Status::CANCELLED;
        }

        // Receive the corresponding get status response message
        proverMessage.Clear();
        bResult = stream->Read(&proverMessage);
        if (!bResult)
        {
            cerr << "Error: AggregatorServiceImpl::Channel() failed calling stream->Read(proverMessage)" << endl;
            return Status::CANCELLED;
        }
        
        // Check type
        if (proverMessage.response_case() != aggregator::v1::ProverMessage::ResponseCase::kGetStatusResponse)
        {
            cerr << "Error: AggregatorServiceImpl::Channel() got proverMessage.response_case=" << proverMessage.response_case() << " instead of GET_STATUS_RESPONSE" << endl;
            return Status::CANCELLED;
        }

        // Check id
        if (proverMessage.id() != aggregatorMessage.id())
        {
            cerr << "Error: AggregatorServiceImpl::Channel() got proverMessage.id=" << proverMessage.id() << " instead of aggregatorMessage.id=" << aggregatorMessage.id() << endl;
            return Status::CANCELLED;
        }

        sleep(1);

        // CALL CANCEL (it should return an error)

        // Send a cancel request message
        aggregatorMessage.Clear();
        messageId++;
        aggregatorMessage.set_id(to_string(messageId));
        aggregator::v1::CancelRequest * pCancelRequest = new aggregator::v1::CancelRequest();
        zkassertpermanent(pCancelRequest != NULL);
        pCancelRequest->set_id("invalid_id");
        aggregatorMessage.set_allocated_cancel_request(pCancelRequest);
        bResult = stream->Write(aggregatorMessage);
        if (!bResult)
        {
            cerr << "Error: AggregatorServiceImpl::Channel() failed calling stream->Write(aggregatorMessage)" << endl;
            return Status::CANCELLED;
        }

        // Receive the corresponding cancel response message
        proverMessage.Clear();
        bResult = stream->Read(&proverMessage);
        if (!bResult)
        {
            cerr << "Error: AggregatorServiceImpl::Channel() failed calling stream->Read(proverMessage)" << endl;
            return Status::CANCELLED;
        }
        
        // Check type
        if (proverMessage.response_case() != aggregator::v1::ProverMessage::ResponseCase::kCancelResponse)
        {
            cerr << "Error: AggregatorServiceImpl::Channel() got proverMessage.response_case=" << proverMessage.response_case() << " instead of CANCEL_RESPONSE" << endl;
            return Status::CANCELLED;
        }

        // Check id
        if (proverMessage.id() != aggregatorMessage.id())
        {
            cerr << "Error: AggregatorServiceImpl::Channel() got proverMessage.id=" << proverMessage.id() << " instead of aggregatorMessage.id=" << aggregatorMessage.id() << endl;
            return Status::CANCELLED;
        }

        // Check cancel result
        if (proverMessage.cancel_response().result() != aggregator::v1::Result::RESULT_ERROR)
        {
            cerr << "Error: AggregatorServiceImpl::Channel() got proverMessage.cancel_response().result()=" << proverMessage.cancel_response().result() << " instead of RESULT_CANCEL_ERROR" << endl;
            return Status::CANCELLED;
        }

        sleep(1);

        // Call GEN PROOF

        if (config.inputFile.size() == 0)
        {
            cerr << "Error: AggregatorServiceImpl::Channel() found config.inputFile empty" << endl;
            exitProcess();
        }
    //::grpc::ClientContext context;
        aggregator::v1::InputProver *pInputProver = new aggregator::v1::InputProver();
        zkassertpermanent(pInputProver != NULL);
        Input input(fr);
        json inputJson;
        file2json(config.inputFile, inputJson);
        zkresult zkResult = input.load(inputJson);
        if (zkResult != ZKR_SUCCESS)
        {
            cerr << "Error: AggregatorServiceImpl::Channel() failed calling input.load() zkResult=" << zkResult << "=" << zkresult2string(zkResult) << endl;
            exitProcess();
        }

        // Parse public inputs
        aggregator::v1::PublicInputs * pPublicInputs = new aggregator::v1::PublicInputs();
        pPublicInputs->set_old_state_root(scalar2ba(input.publicInputsExtended.publicInputs.oldStateRoot));
        pPublicInputs->set_old_acc_input_hash(scalar2ba(input.publicInputsExtended.publicInputs.oldAccInputHash));
        pPublicInputs->set_old_batch_num(input.publicInputsExtended.publicInputs.oldBatchNum);
        pPublicInputs->set_chain_id(input.publicInputsExtended.publicInputs.chainID);
        pPublicInputs->set_fork_id(input.publicInputsExtended.publicInputs.forkID);
        pPublicInputs->set_batch_l2_data(input.publicInputsExtended.publicInputs.batchL2Data);
        pPublicInputs->set_l1_info_root(scalar2ba(input.publicInputsExtended.publicInputs.l1InfoRoot));
        pPublicInputs->set_timestamp_limit(input.publicInputsExtended.publicInputs.timestampLimit);
        pPublicInputs->set_forced_blockhash_l1(scalar2ba(input.publicInputsExtended.publicInputs.forcedBlockHashL1));
        pPublicInputs->set_sequencer_addr(Add0xIfMissing(input.publicInputsExtended.publicInputs.sequencerAddr.get_str(16)));
        pPublicInputs->set_aggregator_addr(Add0xIfMissing(input.publicInputsExtended.publicInputs.aggregatorAddress.get_str(16)));
        pInputProver->set_allocated_public_inputs(pPublicInputs);

        // Parse keys map
        DatabaseMap::MTMap::const_iterator it;
        for (it=input.db.begin(); it!=input.db.end(); it++)
        {
            string key = NormalizeToNFormat(it->first, 64);
            string value;
            vector<Goldilocks::Element> dbValue = it->second;
            for (uint64_t i=0; i<dbValue.size(); i++)
            {
                value += NormalizeToNFormat(fr.toString(dbValue[i], 16), 16);
            }
            (*pInputProver->mutable_db())[key] = value;
        }

        // Parse contracts data
        DatabaseMap::ProgramMap::const_iterator itc;
        for (itc=input.contractsBytecode.begin(); itc!=input.contractsBytecode.end(); itc++)
        {
            string key = NormalizeToNFormat(itc->first, 64);
            string value;
            vector<uint8_t> contractValue = itc->second;
            for (uint64_t i=0; i<contractValue.size(); i++)
            {
                value += byte2string(contractValue[i]);
            }
            (*pInputProver->mutable_contracts_bytecode())[key] = value;
        }

        // Allocate the gen batch request
        aggregator::v1::GenBatchProofRequest *pGenBatchProofRequest = new aggregator::v1::GenBatchProofRequest();
        zkassertpermanent(pGenBatchProofRequest != NULL );
        pGenBatchProofRequest->set_allocated_input(pInputProver);

        // Send the gen proof request
        aggregatorMessage.Clear();
        messageId++;
        aggregatorMessage.set_id(to_string(messageId));
        aggregatorMessage.set_allocated_gen_batch_proof_request(pGenBatchProofRequest);
        bResult = stream->Write(aggregatorMessage);
        if (!bResult)
        {
            cerr << "Error: AggregatorServiceImpl::Channel() failed calling stream->Write(aggregatorMessage)" << endl;
            return Status::CANCELLED;
        }

        // Receive the corresponding get proof response message
        proverMessage.Clear();
        bResult = stream->Read(&proverMessage);
        if (!bResult)
        {
            cerr << "Error: AggregatorServiceImpl::Channel() failed calling stream->Read(proverMessage)" << endl;
            return Status::CANCELLED;
        }
        
        // Check type
        if (proverMessage.response_case() != aggregator::v1::ProverMessage::ResponseCase::kGenBatchProofResponse)
        {
            cerr << "Error: AggregatorServiceImpl::Channel() got proverMessage.response_case=" << proverMessage.response_case() << " instead of GEN_BATCH_PROOF_RESPONSE" << endl;
            return Status::CANCELLED;
        }

        // Check id
        if (proverMessage.id() != aggregatorMessage.id())
        {
            cerr << "Error: AggregatorServiceImpl::Channel() got proverMessage.id=" << proverMessage.id() << " instead of aggregatorMessage.id=" << aggregatorMessage.id() << endl;
            return Status::CANCELLED;
        }

        uuid = proverMessage.gen_batch_proof_response().id();

        // CALL GET PROOF AND CHECK IT IS PENDING

        for (uint64_t i=0; i<5; i++)
        {
            // Send a get proof request message
            aggregatorMessage.Clear();
            messageId++;
            aggregatorMessage.set_id(to_string(messageId));
            aggregator::v1::GetProofRequest * pGetProofRequest = new aggregator::v1::GetProofRequest();
            zkassertpermanent(pGetProofRequest != NULL);
            pGetProofRequest->set_id(uuid);
            aggregatorMessage.set_allocated_get_proof_request(pGetProofRequest);
            bResult = stream->Write(aggregatorMessage);
            if (!bResult)
            {
                cerr << "Error: AggregatorServiceImpl::Channel() failed calling stream->Write(aggregatorMessage)" << endl;
                return Status::CANCELLED;
            }

            // Receive the corresponding get proof response message
            proverMessage.Clear();
            bResult = stream->Read(&proverMessage);
            if (!bResult)
            {
                cerr << "Error: AggregatorServiceImpl::Channel() failed calling stream->Read(proverMessage)" << endl;
                return Status::CANCELLED;
            }
            
            // Check type
            if (proverMessage.response_case() != aggregator::v1::ProverMessage::ResponseCase::kGetProofResponse)
            {
                cerr << "Error: AggregatorServiceImpl::Channel() got proverMessage.response_case=" << proverMessage.response_case() << " instead of GET_PROOF_RESPONSE" << endl;
                return Status::CANCELLED;
            }

            // Check id
            if (proverMessage.id() != aggregatorMessage.id())
            {
                cerr << "Error: AggregatorServiceImpl::Channel() got proverMessage.id=" << proverMessage.id() << " instead of aggregatorMessage.id=" << aggregatorMessage.id() << endl;
                return Status::CANCELLED;
            }

            // Check get proof result
            if (proverMessage.get_proof_response().result() != aggregator::v1::GetProofResponse_Result_RESULT_PENDING)
            {
                cerr << "Error: AggregatorServiceImpl::Channel() got proverMessage.get_proof_response().result()=" << proverMessage.get_proof_response().result() << " instead of RESULT_GET_PROOF_PENDING" << endl;
                return Status::CANCELLED;
            }

            sleep(5);
        }
    }

#ifdef LOG_SERVICE
    cout << "AggregatorServiceImpl::Channel() stream done" << endl;
#endif

    return Status::OK;
}
```

With these changes we are, basically, doing two main things:
1. Timing the time it takes to generate every proof.
2. Removing (commenting out) all the "unnecessary" proofs for our use case. We are basically doing a batch proof and the final SNARK proof.
 
### Recompile the `zkProver`

After those changes, we need to recompile the binary of the `zkProver`, however, in this case, just do the following.

```bash
cd zkevm-prover
make -j
```

It should take much less time to recompile this, compared to the first compilation.

# Creating sample payloads for the prover

In this first test, we are going to create a sample `erc20` transfer input file for the prover, and prove it.

To do this, we need to setup the `zkevm-testvectors` repository.

```bash
cd zkevm-testvectors
# Install packages
npm i
# Compile Solidity Smart Contracts
npx hardhat compile
```

## Understanding the input creation flow

The flow for the files and scripts involved on the creation of the input for the prover is the following:


![prover_inputs.drawio](https://hackmd.io/_uploads/SJL1Ufp7R.png)

So, at the end of the day, we need to run two different scripts: `gen-test-vectors-evm.js` and `calldata-gen-inputs.js`.

The input `gen-erc20.json` should look like this:

```json
[
  {
    "id": 0,
    "description": "Txs to call all functions of OpInvalid contract (test)",
    "sequencerAddress": "0x617b3a3528F9cDd6630fd3301B9c8911F7Bf063D",
    "sequencerPvtKey": "0x28b2b0318721be8c8339199172cd7cc8f5e273800a35616ec893083a4b32c02e",
    "genesis": {
      "accounts": [
        {
          "address": "0x617b3a3528F9cDd6630fd3301B9c8911F7Bf063D",
          "pvtKey": "0x28b2b0318721be8c8339199172cd7cc8f5e273800a35616ec893083a4b32c02e",
          "balance": "100000000000000000000",
          "nonce": "0"
        },
        {
          "address": "0x4d5Cf5032B2a844602278b01199ED191A86c93ff",
          "pvtKey": "0x4d27a600dce8c29b7bd080e29a26972377dbb04d7a27d919adbb602bf13cfd23",
          "balance": "200000000000000000000",
          "nonce": "0"
        }
      ],
      "contracts": [
        {
          "contractName": "Token",
          "paramsDeploy": {
            "types": [
              "string"
            ],
            "values": [
              "HEZ"
            ]
          }
        }
      ]
    },
    "expectedOldRoot": "0x1292a45f711459b4b6dff036a889a430f5137a2d351a64c618885333412131d4",
    "txs": [
      {
        "type": 11,
        "deltaTimestamp": "1944498031",
        "l1Info": {
          "globalExitRoot": "0x090bcaf734c4f06c93954a827b45a6e8c67b8e0fd1e0a35a1c5982d6961828f9",
          "blockHash": "0x24a5871d68723340d9eadc674aa8ad75f3e33b61d5a9db7db92af856a19270bb",
          "timestamp": "42"
        },
        "indexL1InfoTree": 0
      },
      {
        "from": "0x617b3a3528F9cDd6630fd3301B9c8911F7Bf063D",
        "to": "contract",
        "nonce": "0",
        "value": "0",
        "contractName": "Token",
        "function": "mint",
        "params": [
          "0x4d5Cf5032B2a844602278b01199ED191A86c93ff",
          100000000000
        ],
        "gasLimit": 100000,
        "gasPrice": "1000000000",
        "chainId": 1000
      },
      {
        "from": "0x617b3a3528F9cDd6630fd3301B9c8911F7Bf063D",
        "to": "contract",
        "nonce": "1",
        "value": "0",
        "contractName": "Token",
        "function": "mint",
        "params": [
          "0x617b3a3528F9cDd6630fd3301B9c8911F7Bf063D",
          100000000000
        ],
        "gasLimit": 100000,
        "gasPrice": "1000000001",
        "chainId": 1000
      },
      {
        "from": "0x4d5Cf5032B2a844602278b01199ED191A86c93ff",
        "to": "contract",
        "nonce": "0",
        "value": "0",
        "contractName": "Token",
        "function": "transfer",
        "params": [
          "0x617b3a3528F9cDd6630fd3301B9c8911F7Bf063D",
          100
        ],
        "gasLimit": 100000,
        "gasPrice": "1000000000",
        "chainId": 1000
      }
    ],
    "expectedNewRoot": "0x315d091441e0610bc2c5ce325c623daf0ce9333b4d592bed2f8cf3b85598d7a8",
    "expectedNewLeafs": {
      "0x617b3a3528F9cDd6630fd3301B9c8911F7Bf063D": {
        "balance": "100000035701000000000",
        "nonce": "0",
        "storage": null
      },
      "0x4d5Cf5032B2a844602278b01199ED191A86c93ff": {
        "balance": "199999964299000000000",
        "nonce": "1",
        "storage": null
      },
      "0x1275fbb540c8efc58b812ba83b0d0b8b9917ae98": {
        "balance": "0",
        "nonce": "1",
        "storage": {
          "0x0000000000000000000000000000000000000000000000000000000000000002": "0x2e90edd000",
          "0x0000000000000000000000000000000000000000000000000000000000000005": "0x12",
          "0x0000000000000000000000000000000000000000000000000000000000000007": "0x617b3a3528f9cdd6630fd3301b9c8911f7bf063d00",
          "0x5c9164227e4e2850b9fc759a61468f2c11426c1144a6df87b4a501cc3915e91d": "0x174876e79c",
          "0x5eff3f6834f82409f2dbfe5bcddfb5bd62b8ea2ebf2327cfdb9577734aa9a1b2": "0x174876e864",
          "0x0000000000000000000000000000000000000000000000000000000000000003": "0x48455a0000000000000000000000000000000000000000000000000000000006",
          "0x0000000000000000000000000000000000000000000000000000000000000004": "0x48455a0000000000000000000000000000000000000000000000000000000006"
        },
        "hashBytecode": "0x8bb5add6c738db3e7e466dd4a6eb0e53e431ca70850cad3d489bfc574599c7f2",
        "bytecodeLength": 7938
      },
      "0x000000000000000000000000000000005ca1ab1e": {
        "balance": "0",
        "nonce": "0",
        "storage": {
          "0x0000000000000000000000000000000000000000000000000000000000000000": "0x01",
          "0x0000000000000000000000000000000000000000000000000000000000000002": "0x73e6af6f",
          "0xa6eef7e35abe7026729641147f7915573c7e97b47efa546f5f6e3230263bcb49": "0x1292a45f711459b4b6dff036a889a430f5137a2d351a64c618885333412131d4",
          "0x0000000000000000000000000000000000000000000000000000000000000003": "0xcdd0033ac55876a1e56a689b653aedf385431558c4d07fcdca3094e59cefa506"
        }
      }
    },
    "newLocalExitRoot": "0x0000000000000000000000000000000000000000000000000000000000000000",
    "batchHashData": "0x96d9fc19ce67d3f77f7f76405744209b2d4ec5ff562f2320f64ffccf08f5a43a",
    "batchL2Data": "0x0b73e6af6f00000000f86b80843b9aca00830186a0941275fbb540c8efc58b812ba83b0d0b8b9917ae9880b844a9059cbb000000000000000000000000617b3a3528f9cdd6630fd3301b9c8911f7bf063d00000000000000000000000000000000000000000000000000000000000000648203e88080c4997fef2f92ae6cc7c8a6da3970a69259e12a5a22246aa363fd36f3e9cd413254bf80a89f6440b5cf26d3d68a217a314be915f2c1761a85a119e5d88a3f5ffc1bff",
    "chainID": 1000,
    "oldAccInputHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
    "forkID": 9,
    "l1InfoRoot": "0x090bcaf734c4f06c93954a827b45a6e8c67b8e0fd1e0a35a1c5982d6961828f9",
    "timestampLimit": "1944498031"
  }
]
```

In particular, the input file should contain:
- `id`
- `description`
- `sequencerAddress`
- `sequencerPvtKey`
- `genesis` as an array containing:
    - `accounts` as an array where, for each account, contains
        - `address`
        - `pvtKey`
        - `balance`
        - `nonce`
    - `contracts` as an array where, for each invoked contract, contains
        - `contractName`
        - `paramsDeploy` containing
            - `types`
            - `values`
- `expectedOldRoot`
- `txs` containing, first some more information, and then, the transactions
    - `type`
    - `deltaTimestamp`
    - `l1Info`
        - `globalExitRoot`
        - `blockHash`
        - `timestamp`
    - `indexL1InfoTree`
    - (transactions)
        - `from`
        - `to`
        - `nonce`
        - `contractName`
        - `function`
        - `params` as an array containing the params for the function call
        - `gasLimit`
        - `gasPrice`
        - `chainId`
- `expectedNewRoot` (can be empty)
- `expectedNewLeafs` (can be empty)
- `newLocalExitRoot` (can be empty)
- `batchL2Data` (can be empty)
- `chainID`
- `oldAccInputHash`
- `forkID` should be 9
- `l1InfoRoot`
- `timestampLimit`


Take into account that, during the execution of the scripts, the "can be empty" fields will be conveniently populated. 

So, with this in mind, we run both scripts to obtain the input for the executor.

```bash
sudo npx mocha tools-inputs/tools-calldata/gen-test-vectors-evm.js --vectors gen-erc20
```

This will output on `tools-inputs/data/calldata`, taking the compiled Smart Contracts from `zkevm-testvectors/artifacts` and populating data like the abi of the SC, the `data` field on the transactions, among other things.

Finally, let's run the second script.

```bash
sudo npx mocha tools-inputs/generators/calldata-gen-inputs.js --timeout 0 --vectors erc20 --update --output --evm-debug
```

And this will output the input for the executor on `zkevm-testvectors/calldata` under the name of `erc20_0.json`. Let's copy this file (renamed as `input_executor_0.json` since it is harcoded on `aggregator_service.cpp`...) into the correct directory to run the first proof.

```bash
cp inputs-executor/calldata/erc20_0.json ../zkevm-prover/testvectors/e2e/fork_9/input_executor_0.json
```


### TL;DR
```bash
cd zkevm-testvectors
sudo npx mocha tools-inputs/tools-calldata/gen-test-vectors-evm.js --vectors gen-erc20
sudo npx mocha tools-inputs/generators/calldata-gen-inputs.js --timeout 0 --vectors erc20 --update --output --evm-debug
# Renaming the input for the executor because it is hardcoded on the code...
cp inputs-executor/calldata/erc20_0.json ../zkevm-prover/testvectors/e2e/fork_9/input_executor_0.json
```

## Running the prover

Once we have our first input for the prover, let's launch a run of the prover, along with some other commands to verify the proof afterwards.

```bash
cd ..
cd zkevm-prover
time build/zkProver -c testvectors/config_runFile_e2e.json
```

This last command will take a while to finish, and it will start outputing a lot of logs from the prover (that later we will save as `logs`). Once the proof is done, the result is stored inside `zkevm-prover/runtime/output`. Let's verify that the proof is correct!

```bash
snarkjs ffv config/final/final.fflonk.verkey.json $(ls -t runtime/output/*.gen_final_proof_public.json | head -n1) $(ls -t runtime/output/*.final_proof.proof.json | head -n1)
```

This will invoke the fflonk verifier and will output something like the following, if everything went well.

```js
[INFO]  snarkJS: FFLONK VERIFIER STARTED
[INFO]  snarkJS: ----------------------------
[INFO]  snarkJS:   FFLONK VERIFY SETTINGS
[INFO]  snarkJS:   Curve:         bn128
[INFO]  snarkJS:   Circuit power: 24
[INFO]  snarkJS:   Domain size:   16777216
[INFO]  snarkJS:   Public vars:   1
[INFO]  snarkJS: ----------------------------
[INFO]  snarkJS: > Checking commitments belong to G1
[INFO]  snarkJS: > Checking evaluations belong to F
[INFO]  snarkJS: > Checking public inputs belong to F
[INFO]  snarkJS: > Computing challenges
[INFO]  snarkJS: ··· challenges.beta:  606522096090969062360110464429028111150503572719246234524625349866503544411
[INFO]  snarkJS: ··· challenges.gamma: 3222201011337758400501826539142786633125351185631490613765994035086955507292
[INFO]  snarkJS: ··· challenges.xi:    4526593623742623190500458837917392613915431686253498973315922809212451974671
[INFO]  snarkJS: ··· challenges.alpha: 5918191890789152318683771881260908992250910959632005003047814638211141835222
[INFO]  snarkJS: ··· challenges.y:     5363082617575406687134385990071433439014292411776042424376419245235142586972
[INFO]  snarkJS: > Computing Zero polynomial evaluation Z_H(xi)
[INFO]  snarkJS: > Computing Lagrange evaluations
[INFO]  snarkJS: > Computing polynomial identities PI(X)
[INFO]  snarkJS: > Computing r0(y)
[INFO]  snarkJS: ··· Computing r0(y)
[INFO]  snarkJS: > Computing r1(y)
[INFO]  snarkJS: ··· Computing T0(xi)
[INFO]  snarkJS: ··· Computing C1(h_1ω_4^i) values
[INFO]  snarkJS: > Computing r2(y)
[INFO]  snarkJS: ··· Computing T1(xi)
[INFO]  snarkJS: ··· Computing T2(xi)
[INFO]  snarkJS: ··· Computing C2(h_2ω_3^i) values
[INFO]  snarkJS: ··· Computing C2(h_3ω_3^i) values
[INFO]  snarkJS: > Computing F
[INFO]  snarkJS: > Computing E
[INFO]  snarkJS: > Computing J
[INFO]  snarkJS: > Validate all evaluations with a pairing
[INFO]  snarkJS: PROOF VERIFIED SUCCESSFULLY
[INFO]  snarkJS: FFLONK VERIFIER FINISHED
```


# Creating custom payloads

This repository contains the needed packages and scripts to:
- Create some wallets (pair private key/address) to interact with.
- Create some "custom" payloads to be benchmarked by Polygon's zkEVM. In particular, we currently support the following custom payloads
    - `transfers`
    - `erc20`
    - `deploy`
    - `sha256`
    - `precompilesha256`
    - `maxethtransfers` 

You can create more custom payloads implementing them on `runner.py`.

After cloning the repository, you should install the requirements.

```bash
cd python-cross-chain-tx-executor
# If you are missing pip3, please install it:
# sudo apt update
# sudo apt install python3-pip
pip3 install -r requirements.txt
```

After that, we are ready to create, first, a bunch of wallets to interact with

```bash
python3 gen_wallets.py --addresses 205
```

And, finally, create the payloads from the list of possible payloads (described above)

```bash
# replace <your_benchmark> by one of the following: transfers, erc20, deploy, sha256, precompilesha256 or maxethtransfers.
python3 runner.py --node polygon --benchmark <your_benchmark> --addresses wallets.csv
```

After this, you will have your brand new custom payloads inside `python-cross-chain-tx-executor/polygon_bench`.

Let's rename the output directory and proceed with the automating process to benchmark those files.

```bash
mv python-cross-chain-tx-executor/polygon_bench python-cross-chain-tx-executor/polgon_bench_<your_benchmark>
```

# Automating the process

Save the following script on your user directory (in our case, `/home/ubuntu`) as `automatic_benchmark.sh`.
```bash
#!/usr/bin/env bash

test=$1
mkdir -p zkevm-prover/logs_$test
listOfFiles=$(ls python-cross-chain-tx-executor/polygon_bench_$test)

for file in $listOfFiles;
do
    echo "Processing file: $file"
    echo "Copying file to zkevm-testvectors"
    cp python-cross-chain-tx-executor/polygon_bench_$test/$file zkevm-testvectors/tools-inputs/tools-calldata/generate-test-vectors/gen-$file
    cd zkevm-testvectors
    echo "(1/2) Generating inputs for file: $file"
    sudo npx mocha --max-old-space-size=524288 tools-inputs/tools-calldata/gen-test-vectors-evm.js --vectors gen-$file
    echo "(2/2) Generating inputs for file: $file"
    sudo npx mocha --max-old-space-size=524288 tools-inputs/generators/calldata-gen-inputs.js --timeout 0 --vectors $file --update --output --evm-debug

    fileWithoutExtension="${file%.*}"
    echo $fileWithoutExtension
    cd ..
    echo "Copying generated files to testvectors"
    fileOutput="${fileWithoutExtension}_0.json"
    cp zkevm-testvectors/inputs-executor/calldata/$fileOutput zkevm-prover/testvectors/e2e/fork_9/input_executor_0.json
    echo
    cd zkevm-prover
    csv_file="benchmarks.csv"
    echo "Writing file name to csv"
    fileWithComma="$fileWithoutExtension, "
    echo -n "$fileWithComma" >> $csv_file
    echo "Running prover"
    time build/zkProver -c testvectors/config_runFile_e2e.json >> logs_$test/$fileWithoutExtension.log
    echo "Prover done"
    echo
    echo "Moving files to backup"
    mkdir -p testvectors/e2e/fork_9/$fileWithoutExtension
    mv testvectors/e2e/fork_9/*.json testvectors/e2e/fork_9/$fileWithoutExtension

    mkdir -p runtime/output/$fileWithoutExtension
    mv runtime/output/*.json runtime/output/$fileWithoutExtension
    echo "Verifying the proof..."
    snarkjs ffv config/final/final.fflonk.verkey.json $(ls -t runtime/output/$fileWithoutExtension/*.gen_final_proof_public.json | head -n1) $(ls -t runtime/output/$fileWithoutExtension/*.final_proof.proof.json | head -n1)
    cd ..

    echo "Done processing file: $file"
    echo
    echo
done

cp zkevm-prover/benchmarks.csv zkevm-prover/benchmarks_$test.csv
```

Launch the script with the proper testbench, for example

```bash
cd ~
time sh automatic_benchmark.sh transfers
```

This will do, for every custom payload we want to test inside `polygon_bench_transfers`, created through the `python-cross-chain-tx-executor`
1. Create the proper input for the prover (check section "Creating sample payloads for the prover").
2. Copy the input for the prover inside `zkevm-prover` to be proved.
3. Log the file name inside `benchmarks.csv` file.
4. Start the prover with the current file, saving the logs of the prover inside `zkevm-prover/logs_transfers/$fileName.log`.
5. Move the particular input to a backup directory (`zkevm-prover/testvectors/e2e/fork_9/$fileName`)
6. Verify the proof for the current file and print the result on the terminal.
7. Save the outputs from the prover for the current file into a backup directory (`zkevm-prover/runtime/output/$fileName`)