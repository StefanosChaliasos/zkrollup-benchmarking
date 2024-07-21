# Analyzing and Benchmarking ZK-Rollups

This repository contains the code and instructions for benchmarking ZK-Rollups, as described in the paper [**"Analyzing and Benchmarking ZK-Rollups"**](https://eprint.iacr.org/2024/889.pdf) by Stefanos Chaliasos, Itamar Reif, Adria Torralba-Agell, Jens Ernstberger, Akis Kattis, and Benjamin Livshits. This paper will be published at AFT'24.

## Content

This repository includes a main script, `runner.py`, designed to execute a variety of benchmarks for evaluating ZK-Rollups performance. The benchmarks covered are:

* Transfers
* ERC20 Transfers
* Smart Contract Deployment
* SHA256 Hash Computations
* Precompiled SHA256 Hash Computations
* Maximum ETH Transfers

### Benchmark Details

Each benchmark can be run with different input sizes, such as 1 transfer, 10 transfers, etc. For certain benchmarks like transfers, we offer the flexibility to perform all transactions using the same set of addresses or using a different set of addresses for each transaction.

### Additional Scripts

* Generate Address Key Pairs: We provide the `gen_wallets.py` script to generate address-key pairs needed for the benchmarks.
* Post-Processing Results: Various scripts are available to help you post-process and analyze the benchmark results effectively.

### Usage

To get started with the benchmarks, follow the instructions provided in `ERA-INSTRUCTIONS.md` and `POLYGON-INSTRUCTIONS.md` for benchmarking zkSync Era and Polygon's zkEVM respectively.

#### Benchmarking zkSync Era

For detailed instructions on how to benchmark zkSync Era, please refer to [ERA-INSTRUCTIONS.md](./ERA-INSTRUCTIONS.md).

#### Benchmarking Polygon zkEVM

For detailed instructions on how to benchmark Polygon zkEVM, please refer to [POLYGON-INSTRUCTIONS.md](./POLYGON-INSTRUCTIONS.md).

## Contributing

Contributions are welcome! Please submit a pull request if you want to contribute.
