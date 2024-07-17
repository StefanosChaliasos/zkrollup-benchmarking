# Summary

*Special thanks to Ramon Canales and Emil Luta from Matter Labs for discussion and helping with technical issues.*

In this guide, we will set up a machine on the Google Cloud Platform (GCP), install zkSync Era and its dependencies, and finally, produce proofs for arbitrary transactions.

__Note:__ Everything below has been tested on commit [4794286ab1a32fb2f6f2843e76723b7ac2d88ca8](https://github.com/matter-labs/zksync-era/commit/4794286ab1a32fb2f6f2843e76723b7ac2d88ca8) using the GPU prover.

# Create an Instance and Connect

The instance we are going to use has the following configurations:

* **Machine type:** g2-standard-32 (32 vCPUs, 16 cores, 128 GB RAM)
* **CPU platform:** Intel Cascade Lake
* **Architecture:** x86/64
* **GPUs:** 1 x NVIDIA L4
* **Boot disk space:** 1000 GB
* **OS:** Ubuntu 22.04 LTS

At the time of writing, this machine cost US$1.87 per hour. Note that there might be regions that are cheaper, or you can reduce the cost with reserved pricing.

## GCP Instructions

First, login into GCP and go to `Compute Engine` -> `VM Instances` -> `Create Instance` (<https://console.cloud.google.com/compute/instancesAdd>).

Next, we want to correctly configure the machine. In the following screenshot, we highlight the configurations you have to change:

![gcp-screenshot-1](https://hackmd.io/_uploads/SymQcKYyC.png)

Next, scroll down to the `Boot Disk` section and select `change`.

![gcp-screenshot-2](https://hackmd.io/_uploads/r1xrqKYJR.png)

Finally, update the settings as follows.

![gcp-screenshot-3](https://hackmd.io/_uploads/B1Zu5KtyA.png)

## Connect to the machine

Go back to your `VM instances` and connect to the newly created machine by clicking the `SSH` icon.

![gcp-screenshot-4](https://hackmd.io/_uploads/S1IrqcY1C.png)

The, when you connect to you machine enable sudo access without a password.

```
sudo visudo
# Change the line 
# %sudo   ALL=(ALL:ALL) ALL
# to
# %sudo  ALL=(ALL) NOPASSWD: ALL
```

Add your user to sudo users.

```
sudo adduser $USER sudo
```

### Connect to the machine using another terminal

You have two options for adding your SSH key to the machine. Either you can directly add your key to the VM's `~/.ssh/authorized_keys` or use the `gcloud` CLI utility. Note that if you add directly to a VM's `~/.ssh/authorized_keys` files, the VM's guest agent might overwrite them, and you will need to re-do it.

To add them directly, just follow the instructions below.

```
vim .ssh/authorized_keys
# Paste your public key
```

To use `gcloud`, you have to first install it from [here](https://cloud.google.com/sdk/docs/install-sdk). Then, to add your key, run:

```
vim ssh_key
# Add to this file $GOOGLE_USERNAME:$PUBLIC_SSH_KEY
gcloud compute instances add-metadata INSTANCE_NAME \
    --metadata-from-file ssh-keys=ssh_key
```

Finally, to connect to the machine from your terminal, find the external IP from GCP and connect with SSH.

```
ssh google_user_name@external_ip
```

__NOTE:__ Consider running the following commands through a `tmux` session.

# Setup the Machine and Install Dependencies

Instructions are from the [official docs](https://github.com/matter-labs/zksync-era/blob/main/docs/guides/setup-dev.md) along with instructions to install the correct version for `cmake` and all the proper versions of `nvidia` and `cuda` drivers and software.

```
git clone https://github.com/matter-labs/zksync-era.git
cd zksync-era && git checkout 4794286ab1a32fb2f6f2843e76723b7ac2d88ca8 && cd ..

# Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
. "$HOME/.cargo/env"

# NVM
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash

# Reload current shell
. .bashrc

# All necessary stuff
sudo apt update -yqq
sudo apt-get install -yqq build-essential pkg-config clang lldb lld libssl-dev postgresql

# Install cmake 3.24.2
sudo apt-get install -yqq build-essential libssl-dev checkinstall zlib1g-dev libssl-dev && \
wget https://github.com/Kitware/CMake/releases/download/v3.24.2/cmake-3.24.2.tar.gz && \
tar -xzvf cmake-3.24.2.tar.gz && \
cd cmake-3.24.2/ && \
./bootstrap && \
make && \
sudo make install && \
cd ../ && \
echo 'export PATH="/usr/local/bin:$PATH"' >> .bashrc && \
. .bashrc

# Docker
sudo apt install -yqq apt-transport-https ca-certificates curl software-properties-common && \
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add - && \
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable" && \
apt-cache policy docker-ce && \
sudo apt install -yqq docker-ce && \
sudo usermod -aG docker $USER

# You might need to re-connect (due to usermod change).
source .bashrc
newgrp docker

# Run the following command to check that docker is working
# docker ps -a

# SQL tools
cargo install sqlx-cli --version 0.7.3
# Start docker.
sudo systemctl start docker

# Solidity
sudo add-apt-repository ppa:ethereum/ethereum && \
sudo apt-get update -yqq && \
sudo apt-get install -yqq solc

# Node & yarn
nvm install 18
npm install -g yarn
yarn set version 1.22.19

# Install NVIDIA, we need version 12.3.0
sudo apt install -yqq ubuntu-drivers-common && \
sudo apt install -yqq nvidia-driver-550 && \
sudo apt-get install -yqq nvidia-driver-550-open && \
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin && \
sudo mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600 && \
wget https://developer.download.nvidia.com/compute/cuda/12.3.0/local_installers/cuda-repo-ubuntu2204-12-3-local_12.3.0-545.23.06-1_amd64.deb && \
sudo dpkg -i cuda-repo-ubuntu2204-12-3-local_12.3.0-545.23.06-1_amd64.deb && \
sudo cp /var/cuda-repo-ubuntu2204-12-3-local/cuda-*-keyring.gpg /usr/share/keyrings/ && \
sudo apt-get -yqq update && \
sudo apt-get -yqq install cuda-toolkit-12-3 && \
echo 'export PATH="/usr/local/cuda-12.3/bin:$PATH"' >> .bashrc && \
echo 'export LD_LIBRARY_PATH="/usr/local/cuda-12.3/lib64:$LD_LIBRARY_PATH"' >> .bashrc && \
sudo apt-get install -yqq cuda-drivers  
#sudo apt-get install -yqq cuda-drivers-550

# Set zksync variables
echo 'export ZKSYNC_HOME="$HOME/zksync-era"' >> .bashrc && \
echo 'export PATH="$ZKSYNC_HOME/bin:$PATH"' >> .bashrc

# At this point, we need to reboot
sudo reboot

# Stop the postgres database we are going to use the Docker one
sudo systemctl stop postgresql

# Check versions and GPUs using the following commands
# nvcc --version
# nvidia-smi
```

# Install Era and the Prover

## Install Era

Instructions are being adapted from the [official docs](https://github.com/matter-labs/zksync-era/tree/main/prover/prover_fri).

First, change the current directory to `zksync-era.`

```
cd zksync-era
```

Next, we will init Era. The following command will take ~5 minutes.

```
zk && zk init
```

<details>
<summary>Troubleshooting</summary>
If you get the following error:

```
Error: EACCES: permission denied, mkdir'/home/$USER/zksync-era/volumes/reth/data'
```

Then run the following command and retry:

```
sudo chown -R $USER:$USER volumes
```

If you get the following error:

```
Error response from daemon: driver failed programming external connectivity on endpoint zksync-era-postgres-1
```

Remember to shut down the postgres server and retry:

```
sudo systemctl stop postgresql
```

</details>

## Install the Prover

After that, the next step is to set up and compile all prover components. Note that each command will take a while (at most 10-15 mins).

```
cd prover
./setup.sh gpu # This will take close to an hour
zk f cargo build --release --bin zksync_prover_fri_gateway
zk f cargo build --release --bin zksync_witness_generator
zk f cargo build --release --bin zksync_witness_vector_generator
zk f cargo build --features "gpu" --release --bin zksync_prover_fri
zk f cargo build --release --bin zksync_proof_fri_compressor
```

Before continuing, go to the previous directory.

```
cd ..
```


## Control how the transactions are going to be processed in batches

Because we want to process all the transactions in a single batch we should do the following change. We need to update the `CHAIN_STATE_KEEPER_TRANSACTION_SLOTS` to a large value (e.g., 20 seconds) to give the sequencer time to process all the transactions that we want to execute. 

```
vim ~/zksync-era/etc/env/dev.env #(or ~/zksync-era/etc/env/target/dev.env)
# Find CHAIN_STATE_KEEPER_BLOCK_COMMIT_DEADLINE_MS and set it to 5 minutes
# i.e.
# CHAIN_STATE_KEEPER_BLOCK_COMMIT_DEADLINE_MS=300000
# We can also set the limit of transactions to be 5000
CHAIN_STATE_KEEPER_TRANSACTION_SLOTS=5000
```

After doing that, we have to stop the server (i.e., the `zk server` command if we had started it) and restart it.

# Start the Pipeline and Create the First Proof

Let's start the pipeline. Run each command to a different session (consider using tmux). The first one should be run from the root directory, and the others should run from inside the `prover` directory.

```
# Run the server
zk server --components=api,eth,tree,state_keeper,housekeeper,commitment_generator,proof_data_handler
# Run prover gateway
zk f cargo run --release --bin zksync_prover_fri_gateway
# Run four witness generators to generate witnesses for each round
API_PROMETHEUS_LISTENER_PORT=3116 zk f cargo run --release --bin zksync_witness_generator -- --all_rounds
# Run witness vector generators to feed jobs to GPU prover
FRI_WITNESS_VECTOR_GENERATOR_PROMETHEUS_LISTENER_PORT=3420 zk f cargo run --release --bin zksync_witness_vector_generator
# Run prover
zk f cargo run --features "gpu" --release --bin zksync_prover_fri
# Run proof compressor to compress the proof to be sent on L1
zk f cargo run --release --bin zksync_proof_fri_compressor
```

# Inspect the Database

There are two main databases. The first one is the `zksync_local` database, which includes all the tables for the Era network, the sequencer, etc. The second one is the `prover_local` database, which includes all the details for the prover, the batches proved or queued, and debugging information such as error messages and times. 

To connect to the databases, you can use the following commands.

```
psql postgres://postgres:notsecurepassword@localhost/zksync_local
# or
psql postgres://postgres:notsecurepassword@localhost/prover_local
```

I suggest using tools like [DataGrip](https://www.jetbrains.com/datagrip) to query and inspect the database. 

In `DataGrip`, you can connect to the database by adding a new source, selecting `PostgreSQL`, then going to the `SSH/SSL` tab, use an SSH tunnel connection. Then, in the `General` tab, add the following details and connect:

* **Host:** `localhost`
* **Port:** `5432`
* **Authentication:** `User & Password`
* **User:** `postgres`
* **Password:** `notsecurepassword`
* **Database:** `zksync_local` or `prover_local`

Some of the important tables to look for are:

* `zksync_local`
    * `l1_batches`: To check batches being processed, number of transactions and origin per batch, and their metadata.
* `prover_local`
    * `witness_inputs_fri`: To check which batches have been processed by the witness generator and what are the data they need to post as a blob.
    * `prover_jobs_fri`: All the jobs processed by the prover.
    * `proof_compression_jobs_fri`: All the batches that have been finilized.

# Run and Prove Custom Transactions

In this part, we will install any dependencies required to run custom transaction payloads and prove them.

## Fund Accounts in the L2

First we need to fund an L2 address from L1. To do that we first need to install `zksync-cli`. Run the following command and follow the instructions to install it.

```
npx zksync-cli
```

To bridge, run the following command.

```
npx zksync-cli bridge deposit --to 0x36615Cf349d7F6344891B1e7CA7C72883F5dc049 --amount 100 --token 0x0000000000000000000000000000000000000000 --pk 0x7726827caac94a7f9e1b160f7ea819f172f7b6f9d2a97f992c38edeab82d4110 --chain dockerized-node --l1-rpc http://localhost:8545 --rpc http://localhost:3050

Deposit:
 From: 0x36615Cf349d7F6344891B1e7CA7C72883F5dc049 (http://localhost:8545)
 To: 0x36615Cf349d7F6344891B1e7CA7C72883F5dc049 (http://localhost:3050)
 Amount: 100 ETH (Ether)

Deposit sent:
 Transaction hash: 0x4f8fb479858f699c342d8764d587f1d94e419bbf399fada65142f062e059507c

Sender L1 balance after transaction: 99999999999999999899.999711643456143746 ETH (Ether)
```

__NOTE:__ You can reuse this command to bridge more funds or to fund more transactions.

## Install Dependencies

First, let's install the `zksolc` compiler:

```
# Note that you should select the compiler based on your machine.
wget https://github.com/matter-labs/zksolc-bin/raw/main/linux-amd64/zksolc-linux-amd64-musl-v1.4.0
chmod +x zksolc-linux-amd64-musl-v1.4.0
sudo mv zksolc-linux-amd64-musl-v1.4.0 /usr/local/bin/zksolc
```

We also need to install a `solc` version that is supported by `zksolc`.

```
# First, install pip if you haven't already installed it.
sudo apt install python3-pip -yqq
pip3 install solc-select
echo 'export PATH="/home/$USER/.local/bin:$PATH"' >> ~/.bashrc
. .bashrc
solc-select install 0.8.24
solc-select use 0.8.24
```

Check that everything is installed.

```
zksolc --version
EraVM Solidity compiler v1.4.0 (LLVM build 73dc702ab07318d6bfedb598d771663a9079191f)
solc --version
solc, the solidity compiler commandline interface
Version: 0.8.24+commit.e11b9ed9.Linux.g++

```

Next, we will use a repo that provides a Python script to run specific transactions on zkSync Era.

```
git clone git@github.com:StefanosChaliasos/python-cross-chain-tx-executor.git
cd python-cross-chain-tx-executor
```

Next, install the requirements.

```
# Install the dependencies
pip3 install -r requirements.txt
```

Finally, run the transactions (e.g., generate a Greeter contract and call some of its functions). You can inspect the prover's progress further through the logs or the database.

```
python3 runner.py --node zksync --transactions transactions/Greeter.json
# or some ERC20 transactions
python3 runner.py --node zksync --transactions transactions/erc20.json
```

<details>
<summary>Troubleshooting</summary>
If you get the following error when running the Python script:

```
web3.exceptions.ContractLogicError: insufficient balance for transfer
```

This means that you need to fund the initial account further. E.g.:

```
npx zksync-cli bridge deposit --to 0x36615Cf349d7F6344891B1e7CA7C72883F5dc049 \
    --amount 10000000 --token 0x0000000000000000000000000000000000000000 \
    --pk 0x7726827caac94a7f9e1b160f7ea819f172f7b6f9d2a97f992c38edeab82d4110 \
    --chain dockerized-node --l1-rpc http://localhost:8545 \
    --rpc http://localhost:3050
```

</details>

# Benchmarking

First, we need to create and fund some Ethereum wallets.
To do so, run the following commands.

```
python3 gen_wallets.py --addresses 300
./era_bridge_to_wallets.sh wallets.csv
# wait for ~5 mins to make sure that everything has been processed
```

Note: if you want to run the `maxethtransfers` benchmarks you will need to populate 5K addresses. We recomend splitting the file into multiple ones and execute the bridge transactions in parallel.

Then to perform the initial benchmarking of plain ETH transfers, we can run the following command.

```
python3 runner.py --node zksync --benchmark transfers \
    --addresses wallets.csv --timeout 330
```

This will create 7 batches:

* 1 transfer
* 10 transfers between the same addresses
* 100 transfers between the same addresses
* 200 transfers between the same addresses
* 10 transfers between different addresses
* 100 transfers between different addresses
* 200 transfers between different addresses

In the `zksync_local` database, the table `l1_batches` should look like the following.

![Screenshot 2024-05-10 at 10.50.42 AM](https://hackmd.io/_uploads/SkXkfUsMR.png)

Where the batch number 7 is the last batch that has bridge transfers, while batch 8 is the first one from the previous benchmark and batch 200 is the last one.

We support the following benchmarks:

* `transfers`: Perform 1/10/100/200 ETH transfers between two specific addresses or between different addresses. Later, we send transactions in the following order: `a -> b`, `b -> c`, `c -> d `, etc.
* `erc20`: Similar to `transfers`, but for ERC-20 transfers. In this case, 
* `deploy`:  We deploy 1/10/100/200 contracts per batch.
* `sha256`: In this payload we use a custom Solidity contract that performs Sha256 hashes. In the payload we first create a random string of size `64`, the we produce a hash for it, and finally we save it into a file. We have 3 batches, of size 1/10/30.
* `precompilesha256`: The same as previously, but we are using the `keccak256` precompile.
* `maxethtransfers` is the same as `transfers`, but we only use different-addresses mode for 498/996/2490/4980.

# Results

Next, we need to process the results. To do that, we need to query the database to extract all the relevant data.

Before doing so, we need to identify each batch number for our benchmarks and add it to a JSON file in the following format. To do so, you can query the database and use the number of transactions per batch and the order in which you executed the benchmarks to identify which batch matches which payload.

```json
[
    {
        "Batch Number": "8",
        "Title": "1_eth_transfer_same",
        "Description": "1 ETH Transfer Same Address"
    },
    {
        "Batch Number": "9",
        "Title": "10_eth_transfer_same",
        "Description": "10 ETH Transfer Same Address"
    },
    {...}
]
```

You should save that file at `data/era_batches_data.json`. You can find there an existing example file.

To run the analysis execute the following script.

```
# Set you GCP username
GCP_USER_NAME=
# Set the IP address of the machine
GCP_IP=
# Set the path to your private ssh key
GCP_SSH_KEY=/path/to/key
python3 analysis/query_era_db.py \
    --ssh-username $GCP_USER_NAME \
    --ssh-host $GCP_IP \
    --ssh-key $GCP_SSH_KEY \
    --db-password notsecurepassword \
    --json-file data/era_batches_data.json
```

This will result to:

```
SSH tunnel established
Successfully connected to database zksync_local on port 6543
Successfully connected to database prover_local on port 6544
Full table:
                   batch_title  witness_and_proving_time  witness_time  proving_time  proof_compression_time  compressed_state_diffs_size
0          1_eth_transfer_same                       450            32           418                    1087                          283
1         10_eth_transfer_same                       439            33           406                    1077                          588
2        100_eth_transfer_same                       703            41           662                    1040                         3921
3        200_eth_transfer_same                       960            60           900                    1077                         7621
4    10_eth_transfer_different                       399            32           367                    1044                          993
5   100_eth_transfer_different                       771            42           729                    1041                         8122
6   200_eth_transfer_different                      1025            51           974                     904                        13802
7          1_erc_transfer_same                       418            32           386                    1077                          252
8         10_erc_transfer_same                       444            32           412                    1074                          585
9        100_erc_transfer_same                       709            42           667                    1051                         3919
10       200_erc_transfer_same                      1092            51          1041                    1077                         7619
11   10_erc_transfer_different                       449            32           417                    1044                          738
12  100_erc_transfer_different                       769            42           727                    1036                         5599
13  200_erc_transfer_different                      1162            54          1108                    1096                        10999
14           1_contract_deploy                       413            32           381                    1074                          389
15          10_contract_deploy                       538            72           466                    1034                         1876
16         100_contract_deploy                       807            43           764                    1056                        17087
17         200_contract_deploy                      1317           100          1217                    1098                        33987
18           1_sha256_solidity                       498            72           426                    1093                          339
19          10_sha256_solidity                       493            58           435                    1077                          616
20          30_sha256_solidity                       710            58           652                    1090                         1358
21         1_keccak_precompile                       417            33           384                    1082                          339
22        10_keccak_precompile                       447            33           414                    1076                          616
23        30_keccak_precompile                       534            35           499                     900                         1358

Table with witness_and_proving_time and compressed_state_diffs_size columns:
                   batch_title  witness_and_proving_time  compressed_state_diffs_size
0          1_eth_transfer_same                       450                          283
1         10_eth_transfer_same                       439                          588
2        100_eth_transfer_same                       703                         3921
3        200_eth_transfer_same                       960                         7621
4    10_eth_transfer_different                       399                          993
5   100_eth_transfer_different                       771                         8122
6   200_eth_transfer_different                      1025                        13802
7          1_erc_transfer_same                       418                          252
8         10_erc_transfer_same                       444                          585
9        100_erc_transfer_same                       709                         3919
10       200_erc_transfer_same                      1092                         7619
11   10_erc_transfer_different                       449                          738
12  100_erc_transfer_different                       769                         5599
13  200_erc_transfer_different                      1162                        10999
14           1_contract_deploy                       413                          389
15          10_contract_deploy                       538                         1876
16         100_contract_deploy                       807                        17087
17         200_contract_deploy                      1317                        33987
18           1_sha256_solidity                       498                          339
19          10_sha256_solidity                       493                          616
20          30_sha256_solidity                       710                         1358
21         1_keccak_precompile                       417                          339
22        10_keccak_precompile                       447                          616
23        30_keccak_precompile                       534                         1358

Mean proof compression time: 1054.375
Median proof compression time: 1075.0
```

This script basically computes the following:

* Extracts witness time from *witness_inputs_fri* and *scheduler_witness_jobs_fri* tables.
* Computes proving time by querying the following tables and sum the `time_taken` from each row that has the batch ID of a specific payload.
    * *prover_jobs_fri*
    * *node_aggregation_witness_jobs_fri*
    * *leaf_aggregation_witness_jobs_fri*
* Gets the compression (STARK to SNARK) from *proof_compression_jobs_fri* table and gets the mean and median values.
* It gets the total bytes required to be posted into the L1 from the *l1_batches* table (column *compressed_state_diffs*).

## Results

| Batch                          | Proving Time (sec) | State Diff (bytes) |
|--------------------------------|--------------------|---------------------|
| 1_eth_transfer_same            | 450                | 283                 |
| 10_eth_transfer_same           | 439                | 588                 |
| 100_eth_transfer_same          | 703                | 3921                |
| 200_eth_transfer_same          | 960                | 7621                |
| 10_eth_transfer_different      | 399                | 993                 |
| 100_eth_transfer_different     | 771                | 8122                |
| 200_eth_transfer_different     | 1025               | 13802               |
| 1_erc_transfer_same            | 418                | 252                 |
| 10_erc_transfer_same           | 444                | 585                 |
| 100_erc_transfer_same          | 709                | 3919                |
| 200_erc_transfer_same          | 1092               | 7619                |
| 10_erc_transfer_different      | 449                | 738                 |
| 100_erc_transfer_different     | 769                | 5599                |
| 200_erc_transfer_different     | 1162               | 10999               |
| 1_contract_deploy              | 413                | 389                 |
| 10_contract_deploy             | 538                | 1876                |
| 100_contract_deploy            | 807                | 17087               |
| 200_contract_deploy            | 1317               | 33987               |
| 1_sha256_solidity              | 498                | 339                 |
| 10_sha256_solidity             | 493                | 616                 |
| 30_sha256_solidity             | 710                | 1358                |
| 1_keccak_precompile            | 417                | 339                 |
| 10_keccak_precompile           | 447                | 616                 |
| 30_keccak_precompile           | 534                | 1358                |


# Clean and Restart Era

If you want to clean the environment and restart Era, you can use the following command from the repo's root directory.

```
zk && zk clean --all && zk init
```
