from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
import json
import argparse
import sys
import os
import shutil
import subprocess
import tempfile
import hashlib
import csv
import time
import copy
import concurrent.futures

from pathlib import Path
from abc import ABC, abstractmethod
from typing import Any, List
from eth_typing import HexStr
from web3 import Web3
from solcx import install_solc, compile_standard

import web3

from zksync2.core.types import ZkBlockParams
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from zksync2.transaction.transaction_builders import TxFunctionCall
from zksync2.transaction.transaction_builders import TxCreateContract
from zksync2.core.types import EthBlockParams
from zksync2.manage_contracts.contract_encoder_base import ContractEncoder
from eth_account import Account
from eth_utils import to_checksum_address
from eth_utils import remove_0x_prefix


_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


def read_source_code(file_name: str) -> str:
    with open(file_name, 'r') as file:
        return file.read()


def check_executable_exists(executable_name):
    return shutil.which(executable_name) is not None


class BlockchainController(ABC):
    @abstractmethod
    def __init__(self, provider_url, chain_id):
        pass

    def get_address(self, key):
        _, _, address = self.get_account(key)
        return address

    @abstractmethod
    def get_balance(self, addr):
        """
        Get the balance of an address
        """
        pass

    @abstractmethod
    def get_account(self, key=None):
        """
        Generate or retrieve an account based on a key.
        """
        pass

    @abstractmethod
    def transfer(self, from_priv_key, to_addr, amount, gas):
        """
        Transfer native tokens from one account to another.
        """
        pass

    @abstractmethod
    def deploy_contract(self, contract, contract_name, from_priv_key, constructor_args, is_yul=False):
        """
        Deploy a contract to the blockchain.
        """
        pass

    @abstractmethod
    def send_transaction(self, transaction, priv_key, from_addr, gas, include_gas_price):
        """
        Send a transaction to the blockchain.
        """
        pass

    @abstractmethod
    def execute(self, priv_key, contract, contract_address, func_name, func_args, call, amount):
        """
        Execute a transaction in the blockchain.
        """
        pass

    @abstractmethod
    def compile_contract(self, source_code_path, contract_name):
        """
        Compile a contract's source code.
        """
        pass


class EthereumController(BlockchainController):
    def __init__(self, provider_url, chain_id):
        self.w3 = Web3(Web3.HTTPProvider(provider_url))
        if not self.w3.is_connected():
            raise ConnectionError("Unable to connect to the Ethereum node.")
        self.chain_id = chain_id

    def get_balance(self, addr):
        balance_wei = self.w3.eth.get_balance(addr)
        balance_eth = self.w3.from_wei(balance_wei, 'ether')
        return balance_eth

    def get_account(self, key=None):
        if key is None:
            priv_key = Web3.to_hex(os.urandom(32))
            account = self.w3.eth.account.from_key(priv_key)
        else: 
            priv_key = HexStr(key)
            account = self.w3.eth.account.from_key(priv_key)
        return priv_key, account, account.address

    def transfer(self, from_priv_key, to_addr, amount, gas):
        from_addr = self.w3.eth.account.from_key(from_priv_key).address
        amount = Web3.to_wei(amount, 'ether')
        transaction = {
            'to': to_addr,
            'value': amount,
            "chainId": self.chain_id,
            "nonce": self.w3.eth.get_transaction_count(from_addr),
            "from": from_addr,
            "gasPrice": self.w3.eth.gas_price,
            "gas": 500000
        }
        receipt = self.send_transaction(transaction, from_priv_key, from_addr, gas, True)
        return receipt

    def deploy_contract(self, contract_path, contract_name, from_priv_key, constructor_args, is_yul=False):
        from_addr = self.w3.eth.account.from_key(from_priv_key).address
        bytecode, abi, storage_layout = self.compile_contract(contract_path, contract_name)
        contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        transaction = contract.constructor(*constructor_args).build_transaction({
            "chainId": self.chain_id,
            "nonce": self.w3.eth.get_transaction_count(from_addr),
            "from": from_addr,
            "gasPrice": self.w3.eth.gas_price,
        })
        receipt = self.send_transaction(transaction, from_priv_key, from_addr, 8000000, False)
        contract_address = receipt['contractAddress']
        contract_instance = self.w3.eth.contract(address=contract_address, abi=abi)
        return receipt, contract_instance, contract_address, storage_layout

    def send_transaction(self, transaction, priv_key, from_addr, gas, include_gas_price):
        signed_txn = self.w3.eth.account.sign_transaction(transaction, priv_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt

    def execute(self, priv_key, contract, contract_address, func_name, func_args, call, amount):
        amount = Web3.to_wei(amount, 'ether')
        if call:
            value = getattr(contract.functions, func_name)(*func_args).call()
            return None, value
        else:
            from_addr = self.w3.eth.account.from_key(priv_key).address
            transaction = getattr(contract.functions, func_name)(*func_args).build_transaction({
                "chainId": self.chain_id,
                "nonce": self.w3.eth.get_transaction_count(from_addr),
                "from": from_addr,
                'value': amount,
                "gasPrice": self.w3.eth.gas_price,
                "gas": 500000
            })
            tx_receipt = self.send_transaction(transaction, priv_key, from_addr, 5000000, False)
            return tx_receipt, None

    def compile_contract(self, source_code_path, contract_name, is_yul=True):
        src = read_source_code(source_code_path)
        install_solc('0.8.19')  # You can choose the version you want

        if is_yul:
            compiled = compile_standard({
                "language": "Yul",
                "sources": {
                    "Contract.yul": {
                        "content": src
                    }
                },
                "settings": {
                    "outputSelection": {
                        "*": {
                            "*": ["metadata", "evm.bytecode", "evm.sourceMap", "storageLayout"]
                        }
                    }
                }
            })
            bytecode = compiled["contracts"]["Contract.yul"]["Contract1"]["evm"]["bytecode"]["object"]
            abi, storage_layout = get_yul_abi_storage_layout()
            return bytecode, abi, storage_layout
        else:
            compiled_sol = compile_standard({
                "language": "Solidity",
                "sources": {
                    "Contract.sol": {
                        "content": src
                    }
                },
                "settings": {
                    "outputSelection": {
                        "*": {
                            "*": ["metadata", "evm.bytecode", "evm.sourceMap", "storageLayout"]
                        }
                    }
                }
            })
            # Extract bytecode and ABI
            bytecode = compiled_sol['contracts']['Contract.sol'][contract_name]['evm']['bytecode']['object']
            abi = json.loads(compiled_sol['contracts']['Contract.sol'][contract_name]['metadata'])['output']['abi']
            storage_layout = compiled_sol['contracts']['Contract.sol'][contract_name]['storageLayout']

            return bytecode, abi, storage_layout


class PolygonController(EthereumController):
    """We inherit the compile_contract method from the EthereumController class
    """
    def __init__(self, provider_url, chain_id, addresses, gen_template=False):
        assert provider_url is None
        assert chain_id == 1000
        self.chain_id = chain_id
        self.gen_template = gen_template

        # Extra fields for the Polygon network
        self.template = None
        self.genesis = None
        self.txs = None
        self.address_map = None
        self.nonces = None

        template_file = os.path.join(_CURRENT_DIR, "templates", "polygon_gen_template.json")
        with open(template_file, "r") as f:
            # The ammendable fields are:
            # - append self.template[0]["genesis"]["accounts"]
            # - append self.template[0]["genesis"]["contracts"]
            # - append self.template[0]["txs"]
            self.template = json.load(f)
            self.genesis = self.template[0]["genesis"]["accounts"]
            self.txs = self.template[0]["txs"]

        # Add the addresses to genesis, addresses is a list of lists of priv_key,address
        self.address_map = {row[0]: row[1] for row in addresses}
        for priv, addr in self.address_map.items():
            self.genesis.append({
               "address": addr,
               "nonce": "0",
               "balance": "1000000000000000000000000000",
               "pvtKey": priv
            })
        self.nonces = {g["address"]: int(g["nonce"]) for g in self.genesis}

    # currently supporting only using a single contract in the new batch
    def set_new_batch(self, contract_name, params_deploy):
        template_file = os.path.join(_CURRENT_DIR, "templates", "polygon_gen_template.json")
        temp_template = None
        with open(template_file, "r") as f:
            temp_template = json.load(f)[0]
        temp_template["id"] = 1
        self.template.append(temp_template)
        temp_genesis = copy.deepcopy(self.template[0]["genesis"]["accounts"])
        for el in temp_genesis:
            el["nonce"] = str(self.nonces[el["address"]])
        self.template[-1]["genesis"]["accounts"] = temp_genesis
        self.template[-1]["genesis"]["contracts"] = [{
            "contractName": contract_name,
            "paramsDeploy": params_deploy
        }]
        self.genesis = temp_genesis
        self.txs = self.template[-1]["txs"]


    def get_nonce(self, addr):
        """Get the nonce for a given address and increment it by 1"""
        assert addr in self.nonces
        nonce = self.nonces[addr]
        self.nonces[addr] += 1 
        return nonce

    def get_address(self, key):
        assert key in self.address_map
        return self.address_map[key]

    def get_balance(self, addr):
        raise NotImplementedError("get_balance is not supported")

    def get_account(self, key=None):
        raise NotImplementedError("get_account is not supported")

    def transfer(self, from_priv_key, to_addr, amount, gas):
        from_addr = self.get_address(from_priv_key)
        amount = Web3.to_wei(amount, 'ether')
        transaction = {
            'to': to_addr,
            'value': str(amount),
            "chainId": self.chain_id,
            "nonce": self.get_nonce(from_addr),
            "from": from_addr,
            "gasPrice": "1000000000",
            "gasLimit": 1000000000
        }
        receipt = self.send_transaction(transaction, from_priv_key, from_addr, gas, True)
        return receipt

    def deploy_contract(self, contract_path, contract_name, from_priv_key, constructor_args, is_yul=False):
        assert self.gen_template
        from_addr = self.get_address(from_priv_key)
        transaction = {
            "from": from_addr,
            "to": "deploy",
            "nonce": self.get_nonce(from_addr),
            "value": "0",
            "contractName": contract_name,
            "params": constructor_args,
            "gasLimit": 10000000,
            "gasPrice": "1000000000",
            "chainId": self.chain_id
        }
        receipt = self.send_transaction(transaction, from_priv_key, from_addr, None, True)
        # Return the transaction instead of a receipt
        # Return contract name instead of contract address
        return receipt, None, contract_name, None

    def send_transaction(self, transaction, priv_key, from_addr, gas, include_gas_price):
        # Instead of the receipt just add the transaction to the batch and return the JSON
        self.txs.append(transaction)
        return transaction

    def execute(self, priv_key, contract, contract_address, func_name, func_args, call, amount):
        assert self.gen_template
        amount = Web3.to_wei(amount, 'ether')
        if call:
            raise NotImplementedError("call is not implemented yet")
        else:
            from_addr = self.get_address(priv_key)
            transaction = {
                "from": from_addr,
                "to": "contract",
                "nonce": self.get_nonce(from_addr),
                "value": amount,
                "contractName": contract_address,
                "function": func_name,
                "params": func_args,
                "gasLimit": 100000,
                "gasPrice": "1000000000",
                "chainId": self.chain_id
            }
            tx_receipt = self.send_transaction(transaction, priv_key, from_addr, None, False)
            return tx_receipt, None


def run_zksolc(file_path, is_yul):
    if is_yul:
        cmd: list[Unknown]  = ["zksolc", "--yul", "--bin", file_path]
    else:
        cmd: list[Unknown]  = ["zksolc", "--combined-json", "abi,bin,storage-layout", file_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Check if zksolc completed successfully
    if result.returncode != 0:
        print(f"zksolc failed with the following error:\n{result.stderr}")

    try:
        # Parsing the output
        if is_yul:
            bytecode = result.stdout.strip().split(' ')[-1]
            abi, storage_layout = get_yul_abi_storage_layout()
            data = {
                'contracts': {file_path + ":Contract1": {
                    'abi': abi, 'storage-layout': storage_layout, 
                    'bin': bytecode, 'factory-deps': {}
                }},
                # Use some hardcoded values here
                'version': '0.8.20+commit.a1b79de6.Darwin.appleclang', 'zk_version': '1.3.13'
            }
        else:
            data = json.loads(result.stdout)
        return data

    except json.JSONDecodeError as e:
        # Handle JSON parsing errors
        print(f"Failed to parse zksolc output as JSON. Error: {e}")
        sys.exit(1)


class ZkSyncController(BlockchainController):
    def __init__(self, provider_url, chain_id):
        self.w3 = ZkSyncBuilder.build(provider_url)
        #if not self.w3.is_connected():
        #    raise ConnectionError("Unable to connect to the zksync node.")
        self.chain_id = chain_id

    def get_balance(self, addr):
        balance_wei = self.w3.eth.get_balance(addr)
        balance_eth = self.w3.from_wei(balance_wei, 'ether')
        return balance_eth

    def get_account(self, key=None):
        if key is None:
            priv_key = Web3.to_hex(os.urandom(32))
            account = Account.from_key(priv_key)
        else: 
            priv_key = HexStr(key)
            account = Account.from_key(priv_key)
        return priv_key, account, account.address

    def transfer(self, from_priv_key, to_addr, amount, gas):
        account = Account.from_key(from_priv_key)
        from_addr = account.address
        # Signer is used to generate signature of provided transaction
        signer = PrivateKeyEthSigner(account, self.chain_id)

        # Get nonce of ETH address on zkSync network
        nonce = self.w3.zksync.get_transaction_count(
            from_addr, ZkBlockParams.COMMITTED.value
        )

        # Get current gas price in Wei
        gas_price = self.w3.zksync.gas_price

        # Create transaction
        tx_func_call = TxFunctionCall(
            chain_id=self.chain_id,
            nonce=nonce,
            from_=from_addr,
            to=to_checksum_address(to_addr),
            value=self.w3.to_wei(amount, "ether"),
            data=HexStr("0x"),
            gas_limit=0,  # UNKNOWN AT THIS STATE
            gas_price=gas_price,
            max_priority_fee_per_gas=100_000_000,
        )

        # ZkSync transaction gas estimation
        estimate_gas = self.w3.zksync.eth_estimate_gas(tx_func_call.tx)

        # Convert transaction to EIP-712 format
        tx_712 = tx_func_call.tx712(estimate_gas)

        # Sign message & encode it
        signed_message = signer.sign_typed_data(tx_712.to_eip712_struct())

        # Encode signed message
        msg = tx_712.encode(signed_message)

        # Transfer ETH
        tx_hash = self.w3.zksync.send_raw_transaction(msg)

        # Wait for transaction to be included in a block
        tx_receipt = self.w3.zksync.wait_for_transaction_receipt(
            tx_hash, timeout=240, poll_latency=0.5
        )
        return tx_receipt

    def deploy_contract(self, contract_path, contract_name, from_priv_key, constructor_args, is_yul=False):
        account = Account.from_key(from_priv_key)
        # Signer is used to generate signature of provided transaction
        signer = PrivateKeyEthSigner(account, self.chain_id)

        # Get nonce of ETH address on zkSync network

        nonce = self.w3.zksync.get_transaction_count(
            account.address, EthBlockParams.PENDING.value
        )

        # Get current gas price in Wei
        gas_price = self.w3.zksync.gas_price

        compiled_contract = self.compile_contract(contract_path, contract_name, is_yul)
        t_contract = contract_path + ":" + contract_name
        compiled_contract['contracts'] = {
            t_contract: compiled_contract['contracts'][t_contract]
        }

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w+', suffix=".json") as tmp_file:
            json.dump(compiled_contract, tmp_file)
            tmp_file.flush()  # Ensure that all data is written to the file before reading it elsewhere
            tmp_file_path = Path(tmp_file.name)
            encoded_contract = ContractEncoder.from_json(self.w3, tmp_file_path)[0]

        # Encode the constructor arguments
        encoded_constructor = encoded_contract.encode_constructor(*constructor_args)

        # Create deployment contract transaction
        create_contract = TxCreateContract(
            web3=self.w3,
            chain_id=self.chain_id,
            nonce=nonce,
            from_=account.address,
            gas_limit=0,  # UNKNOWN AT THIS STATE
            gas_price=gas_price,
            bytecode=encoded_contract.bytecode,
            call_data=encoded_constructor,
        )

        # ZkSync transaction gas estimation
        estimate_gas = self.w3.zksync.eth_estimate_gas(create_contract.tx)

        # Convert transaction to EIP-712 format
        tx_712 = create_contract.tx712(estimate_gas)

        # Sign message
        signed_message = signer.sign_typed_data(tx_712.to_eip712_struct())

        # Encode signed message
        msg = tx_712.encode(signed_message)

        # Deploy contract
        tx_hash = self.w3.zksync.send_raw_transaction(msg)

        # Wait for deployment contract transaction to be included in a block
        tx_receipt = self.w3.zksync.wait_for_transaction_receipt(
            tx_hash, timeout=240, poll_latency=0.5
        )
        storage_layout = compiled_contract['contracts'][contract_path +':' + contract_name]['storage-layout']
        return tx_receipt, encoded_contract, tx_receipt["contractAddress"], storage_layout

    def execute(self, priv_key, contract, contract_address, func_name, func_args, call, amount):
        account = Account.from_key(priv_key)
        if call:
            value = getattr(contract.contract.functions, func_name)(*func_args).call({
                "from": account.address,
                "to": contract_address
            })
            return None, value
        else:
            gas_price = self.w3.zksync.gas_price

            # Get nonce of ETH address on zkSync network
            nonce = self.w3.zksync.get_transaction_count(account.address, EthBlockParams.LATEST.value)

            # Execute function
            try:
                tx = getattr(contract.contract.functions, func_name)(*func_args).build_transaction({
                    "nonce": nonce,
                    "from": account.address,
                    "value": self.w3.to_wei(amount, "ether"),
                    "maxPriorityFeePerGas": 1_000_000,
                    "maxFeePerGas": gas_price,
                    "to": contract_address
                })
                # Sign transaction
                signed = account.sign_transaction(tx)

                # Send transaction to zkSync network
                tx_hash = self.w3.zksync.send_raw_transaction(signed.rawTransaction)

                # Wait for transaction to be finalized
                receipt = self.w3.zksync.wait_for_transaction_receipt(tx_hash)
            except web3.exceptions.ContractLogicError as e:
                print("ContractLogicError:", e)
                receipt = {"status": 0}

            return receipt, None

    def send_transaction(self, transaction, priv_key, from_addr, gas, include_gas_price):
        raise NotImplementedError

    def compile_contract(self, source_code_path, contract_name, is_yul): 
        if not check_executable_exists("zksolc"):
            print("Error: zksolc compiler is not installed")
            sys.exit(1)
        combined_json = run_zksolc(source_code_path, is_yul)
        return combined_json

########################## Run TXs from JSON specs ############################

def transfer(controller, from_priv_key, to_addr, amount, gas):
    receipt = controller.transfer(
        from_priv_key, to_addr, amount, gas
    )
    return receipt

def deploy_contract(controller, contract_name, contract_src, is_yul, from_priv_key, constructor_args):
    receipt, contract_instance, contract_address, storage_layout = controller.deploy_contract(
        contract_src, contract_name, from_priv_key, constructor_args, is_yul
    )
    return receipt, contract_instance, contract_address, storage_layout

def execute(
        controller, from_priv_key, contract_instance, contract_address, 
        func_name, func_args, call, amount
    ):
    receipt, returned_value = controller.execute(
            from_priv_key, contract_instance, contract_address, 
            func_name, func_args, call, amount
    )
    return receipt, returned_value

def execute_txs(controller, transactions_json):
    with open(transactions_json, 'r') as f:
        data = json.load(f)

    # Compute accounts' addresses
    print("=== Compute accounts' addresses ===")
    for name, pv in data["accounts"]["pv"].items():
        address = data["accounts"]["address"].get(name)
        if address is None:
            _, _, address = controller.get_account(pv)
            data["accounts"]["address"][name] = address
        print("=>", pv, address)

    print("=== Execute transactions ===")
    for counter, transaction in enumerate(data["transactions"]):
        tx_type = transaction["type"]
        tx_args = transaction["args"]
        tx_id = transaction["id"]
        print("=>", f"TX-{counter}", tx_id)

        if tx_type == "transfer":
            from_priv_key = eval("data" + tx_args["from_priv_key"])
            to_addr = eval("data" + tx_args["to_addr"])
            amount = tx_args["amount"]
            gas = tx_args["gas"]

            receipt = transfer(controller, from_priv_key, to_addr, amount, gas)

        if tx_type == "deploy_contract":
            contract_name = tx_args["contract_name"]
            contract_src = data["contracts"][contract_name]["path"]
            is_yul = contract_src.split('.')[-1] == "yul"
            from_priv_key = eval("data" + tx_args["from_priv_key"])
            constructor_args = tx_args["constructor_args"]
            # Replace any argument that is from the state with its current
            # value. We mainly do that to get addresses
            for i, element in enumerate(constructor_args):
                if isinstance(element, str) and element.startswith('data['):
                    constructor_args[i] = eval(element)
            receipt, contract_instance, contract_address, storage_layout = deploy_contract(
                controller, contract_name, contract_src, is_yul, from_priv_key, constructor_args
            )
            print(receipt)
            data["contracts"][contract_name]["instance"] = contract_instance
            data["contracts"][contract_name]["address"] = contract_address
            data["contracts"][contract_name]["storage_layout"] = storage_layout

        if tx_type == "execute":
            from_priv_key = eval("data" + tx_args["from_priv_key"])
            contract_instance = eval("data" + tx_args["contract_instance"])
            contract_address = eval("data" + tx_args["contract_address"])
            storage_layout = eval("data" + tx_args["storage_layout"])
            contract_name = tx_args["contract_name"]
            func_name = tx_args["func_name"]
            func_args = tx_args["func_args"]
            amount = tx_args.get("amount", 0)
            for i, element in enumerate(func_args):
                if isinstance(element, str) and element.startswith('data['):
                    func_args[i] = eval(element)
            call = tx_args["call"]

            to_addr = contract_address

            receipt, returned_value = execute(
                controller,
                from_priv_key, 
                contract_instance, 
                contract_address, 
                func_name, 
                func_args, 
                call, 
                amount
            )
            print("-->tx_receipt\n", receipt)
            print("-->returned_value\n", returned_value)

###############################################################################

############################## Run Benchmarks #################################
def transfer_task(controller, from_priv_key, to_addr, amount, gas):
    receipt = transfer(controller, from_priv_key, to_addr, amount, gas)
    return receipt


def benchmark_transfers_block(controller, addresses, timeout, nr_transfers, amount, gas, is_different=False, is_parallel=False):
    assert len(addresses) >= nr_transfers, f"Not enough addresses for transfers benchmark. Need at least {nr_transfers}."
    # variables to keep track of elapsed time and how much time we need to wait
    start = 0
    elapsed = 0
    to_wait = 0

    if not is_different:
        from_priv_key = addresses[0][0]
        to_addr = addresses[1][1]

    # If it is a PolygonController we need to create a new instance every time
    if isinstance(controller, PolygonController):
        controller = PolygonController(None, controller.chain_id, addresses)

    print("=======", f"{nr_transfers} transfer(s)", "=======")
    start = time.time()

    if is_parallel and not isinstance(controller, PolygonController):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for i in range(0, nr_transfers):
                if is_different:
                    from_priv_key = addresses[i][0]
                    to_addr = addresses[i+1][1]
                futures.append(
                    executor.submit(transfer_task, controller, from_priv_key, to_addr, amount, gas)
                )
            # Wait for all futures to complete
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            total_succeed = sum(1 for r in results if r['status'] == 1)
            total_failed = sum(1 for r in results if r['status'] != 1)
            print("Total succeed", total_succeed)
            print("Total failed", total_failed)

    else:
        for i in range(0, nr_transfers):
            if is_different:
                from_priv_key = addresses[i][0]
                to_addr = addresses[i+1][1]
            receipt = transfer(controller, from_priv_key, to_addr, amount, gas)
            if not isinstance(controller, PolygonController):
                print("Receipt status:", receipt["status"])

    elapsed = time.time() - start
    to_wait = timeout - elapsed
    print("===>Elapsed time:", elapsed, ", We have to wait:", to_wait, "sec")
    # If we are using Polygon we do not need to wait
    if not isinstance(controller, PolygonController):
        time.sleep(to_wait)
    # but we need to save the results into a JSON
    else:
        # Let's save the results into a JSON
        is_same = "same" if not is_different else "different"
        result_name = os.path.join(_CURRENT_DIR, "polygon_bench", f"{nr_transfers}_{is_same}_transfers.json")
        with open(result_name, 'w') as f:
            json.dump(controller.template, f, indent=4)


def benchmark_transfers(controller, addresses, timeout):
    assert len(addresses) >= 200, "Not enough addresses for transfers benchmark. Need at least 200."
    amount = 1
    gas = 21000

    print("=======", "Same Addresses", "=======")
    benchmark_transfers_block(controller, addresses, timeout, 1, amount, gas)
    benchmark_transfers_block(controller, addresses, timeout, 10, amount, gas)
    benchmark_transfers_block(controller, addresses, timeout, 100, amount, gas)
    benchmark_transfers_block(controller, addresses, timeout, 200, amount, gas)
    print("============================")
    print("=======", "Different Addresses", "=======")
    benchmark_transfers_block(controller, addresses, timeout, 10, amount, gas, is_different=True)
    benchmark_transfers_block(controller, addresses, timeout, 100, amount, gas, is_different=True)
    benchmark_transfers_block(controller, addresses, timeout, 200, amount, gas, is_different=True)
    print("=================================")


def benchmark_transfers_max(controller, addresses, timeout):
    assert len(addresses) >= 4980, "Not enough addresses for max transfers benchmark. Need at least 4980."
    amount = 1
    gas = 21000

    print("=======", "Different Addresses", "=======")
    benchmark_transfers_block(controller, addresses, timeout, 498, amount, gas, is_different=True, is_parallel=True)
    benchmark_transfers_block(controller, addresses, timeout, 996, amount, gas, is_different=True, is_parallel=True)
    benchmark_transfers_block(controller, addresses, timeout, 2490, amount, gas, is_different=True, is_parallel=True)
    benchmark_transfers_block(controller, addresses, timeout, 4980, amount, gas, is_different=True, is_parallel=True)
    print("=================================")


def benchmark_erc20_block(
        controller, addresses, timeout, nr_transfers, 
        amount, contract_instance, contract_address, is_different=False):
    # variables to keep track of elapsed time and how much time we need to wait
    start = 0
    elapsed = 0
    to_wait = 0

    if not is_different:
        from_priv_key = addresses[0][0]
        to_addr = addresses[1][1]

    # If it is a PolygonController we need to create a copy of the controller that
    # includes the mint transactions and reset it to that after every block.
    # This should also be safe for nonce management
    # TODO: maybe we should reset the nonces as well because of the hack of
    # setting the results of mint transactions directly into storage.
    if isinstance(controller, PolygonController):
        initial_controller = copy.deepcopy(controller)
    print("=======", f"{nr_transfers} transfer(s)", "=======")
    start = time.time()
    for i in range(0, nr_transfers):
        if is_different:
            from_priv_key = addresses[i][0]
            to_addr = addresses[i+1][1]
        receipt, _ = execute(
            controller, from_priv_key, contract_instance, 
            contract_address, "transfer", [to_addr, amount], 
            False, 0
        )
        if not isinstance(controller, PolygonController):
            print("Receipt status:", receipt["status"])
    elapsed = time.time() - start
    to_wait = timeout - elapsed
    print("===>Elapsed time:", elapsed, ", We have to wait:", to_wait, "sec")
    # If we are using Polygon we do not need to wait
    if not isinstance(controller, PolygonController):
        time.sleep(to_wait)
    # but we need to save the results into a JSON
    else:
        # Let's save the results into a JSON
        is_same = "same" if not is_different else "different"
        result_name = os.path.join(_CURRENT_DIR, "polygon_bench", f"gen-{nr_transfers}_{is_same}_erc20_transfers.json")
        with open(result_name, 'w') as f:
            json.dump(controller.template, f, indent=4)
        # Reset the controller.
        controller = initial_controller

def benchmark_erc20(controller, addresses, timeout):
    assert len(addresses) >= 200, "Not enough addresses for ERC20 benchmark. Need at least 200."
    # Initialize the ERC20 contract
    owner_priv_key = addresses[0][0]
    owner_address = addresses[0][1]

    # First thing we need to deploy the contract
    print("======== Initialize ERC20 contract ========")
    constructor_args = [
        owner_address, owner_address,
        "WETH coin", "WETH", 18
    ]
    receipt, contract_instance, contract_address, _ = controller.deploy_contract(
        "contracts/erc20.sol", "ERC20Template", owner_priv_key, constructor_args
    )
    print("Contract deployed at:", contract_address)
    if not isinstance(controller, PolygonController):
        print("Receipt status:", receipt["status"])
    # Then we need to mint tokens to all the addresses
    for i in addresses:
        address = i[1]
        # Mint 100000 tokens
        receipt, _ = execute(
            controller,
            owner_priv_key, contract_instance, contract_address, 
            "mint", [address, 100000], False, 0
        )
        if not isinstance(controller, PolygonController):
            print("Receipt status:", receipt["status"])
    print("Tokens minted")
    if not isinstance(controller, PolygonController):
        print(f"We have to wait for a complete block to be mined ({timeout+10} sec)")
        time.sleep(timeout+10)
    else:
        # We have to create a new batch
        params = {
            "types": ["address", "address", "string", "string", "uint8"],
            "values": constructor_args
        }
        controller.set_new_batch("ERC20Template", params)
    print("==========================================")

    # Finally we can start transferring tokens
    amount = 10
    print("=======", "Same Addresses", "=======")
    benchmark_erc20_block(controller, addresses, timeout, 1, amount, contract_instance, contract_address)
    benchmark_erc20_block(controller, addresses, timeout, 10, amount, contract_instance, contract_address)
    benchmark_erc20_block(controller, addresses, timeout, 100, amount, contract_instance, contract_address)
    benchmark_erc20_block(controller, addresses, timeout, 200, amount, contract_instance, contract_address)
    print("============================")
    print("=======", "Different Addresses", "=======")
    benchmark_erc20_block(controller, addresses, timeout, 10, amount, contract_instance, contract_address, is_different=True)
    benchmark_erc20_block(controller, addresses, timeout, 100, amount, contract_instance, contract_address, is_different=True)
    benchmark_erc20_block(controller, addresses, timeout, 200, amount, contract_instance, contract_address, is_different=True)
    print("=================================")


def benchmark_deploy_block(controller, addresses, timeout, nr_deployments):
    assert len(addresses) >= nr_deployments, f"Not enough addresses for deploy benchmark. Need at least {nr_deployments}."
    # variables to keep track of elapsed time and how much time we need to wait
    start = 0
    elapsed = 0
    to_wait = 0

    # If it is a PolygonController we need to create a new instance every time
    if isinstance(controller, PolygonController):
        initial_controller = copy.deepcopy(controller)

    print("=======", f"{nr_deployments} deployment(s)", "=======")
    start = time.time()
    for i in range(0, nr_deployments):
        from_priv_key = addresses[i][0]
        constructor_args = [10]
        receipt, _, _, _ = controller.deploy_contract(
            "contracts/Greeter.sol", "Greeter", from_priv_key, constructor_args
        )
        if not isinstance(controller, PolygonController):
            print("Receipt status:", receipt["status"])
    elapsed = time.time() - start
    to_wait = timeout - elapsed
    print("===>Elapsed time:", elapsed, ", We have to wait:", to_wait, "sec")
    # If we are using Polygon we do not need to wait
    if not isinstance(controller, PolygonController):
        time.sleep(to_wait)
    # but we need to save the results into a JSON
    else:
        # Let's save the results into a JSON
        result_name = os.path.join(_CURRENT_DIR, "polygon_bench", f"gen-deploy_{nr_deployments}.json")
        with open(result_name, 'w') as f:
            json.dump(controller.template, f, indent=4)
        # Reset the controller.
        controller = initial_controller


def benchmark_deploy(controller, addresses, timeout):
    assert len(addresses) >= 200, "Not enough addresses for deploy benchmark. Need at least 200."
    print("=======", "Start Benchmarking", "=======")
    benchmark_deploy_block(controller, addresses, timeout, 1)
    benchmark_deploy_block(controller, addresses, timeout, 10)
    benchmark_deploy_block(controller, addresses, timeout, 100)
    benchmark_deploy_block(controller, addresses, timeout, 200)
    print("=====================================")


def benchmark_sha256_block(
        controller, addresses, timeout, nr_hashes, 
        contract_instance, contract_address):
    assert len(addresses) >= 1, "Not enough addresses for SHA256 benchmark. Need at least 1."
    # variables to keep track of elapsed time and how much time we need to wait
    start = 0
    elapsed = 0
    to_wait = 0

    from_priv_key = addresses[0][0]

    # If it is a PolygonController we need to create a new instance every time
    if isinstance(controller, PolygonController):
        initial_controller = copy.deepcopy(controller)

    print("=======", f"{nr_hashes} hashes(s)", "=======")
    start = time.time()
    for i in range(0, nr_hashes):
        receipt, _ = execute(
            controller, from_priv_key, contract_instance, 
            contract_address, "random_hash_save", [], 
            False, 0
        )
        if not isinstance(controller, PolygonController):
            print("Receipt status:", receipt["status"])
    elapsed = time.time() - start
    to_wait = timeout - elapsed
    print("===>Elapsed time:", elapsed, ", We have to wait:", to_wait, "sec")
    # If we are using Polygon we do not need to wait
    if not isinstance(controller, PolygonController):
        time.sleep(to_wait)
    # but we need to save the results into a JSON
    else:
        # Let's save the results into a JSON
        result_name = os.path.join(_CURRENT_DIR, "polygon_bench", f"gen-{contract_address}_{nr_hashes}.json")
        with open(result_name, 'w') as f:
            json.dump(controller.template, f, indent=4)
        # Reset the controller.
        controller = initial_controller

def benchmark_sha256(controller, addresses, timeout, contract_src, contract_name):
    assert len(addresses) >= 1, "Not enough addresses for SHA256 benchmark. Need at least 1."
    # Initialize the SHA256 contract
    owner_priv_key = addresses[0][0]

    # First thing we need to deploy the contract
    print(f"======== Initialize SHA256 contract ({contract_name}) ========")
    constructor_args = []
    receipt, contract_instance, contract_address, _ = controller.deploy_contract(
        contract_src, contract_name, owner_priv_key, constructor_args
    )
    print("Contract deployed at:", contract_address)
    if not isinstance(controller, PolygonController):
        print("Receipt status:", receipt["status"])
        time.sleep(timeout+10)
    else:
        # We have to create a new batch
        params = {
            "types": [],
            "values": constructor_args
        }
        controller.set_new_batch(contract_name, params)
    print(f"We have to wait for a complete block to be mined ({timeout+10} sec)")
    print("====================================================")

    print("=======", "Benchmarking hashes", "=======")
    benchmark_sha256_block(controller, addresses, timeout, 1, contract_instance, contract_address)
    benchmark_sha256_block(controller, addresses, timeout, 10, contract_instance, contract_address)
    benchmark_sha256_block(controller, addresses, timeout, 30, contract_instance, contract_address)
    print("============================")

###############################################################################

def main(args):
    print("Connect to node")
    if args.benchmark:
        with open(args.addresses, 'r') as f:
            reader = csv.reader(f)
            addresses = [row for row in reader]
    if args.node == "geth":
        node_url = "http://0.0.0.0:8547"  
        chain_id = 1337
        controller = EthereumController(node_url, chain_id)
    elif args.node == "zksync":
        node_url = "http://localhost:3050"  
        chain_id = 270
        controller = ZkSyncController(node_url, chain_id)
    elif args.node == "zksync-in-memory":
        node_url = "http://127.0.0.1:8011" 
        chain_id = 260
        controller = ZkSyncController(node_url, chain_id)
    elif args.node == "polygon":
        node_url = None
        chain_id = 1000
        # Check if _CURRENT_DIR/polygon_bench exists
        if not os.path.exists(os.path.join(_CURRENT_DIR, "polygon_bench")):
            os.mkdir(os.path.join(_CURRENT_DIR, "polygon_bench"))
        controller = PolygonController(node_url, chain_id, addresses, gen_template=True)
    else:
        print("Error: Node {node} is not supported")
        sys.exit(1)
    if args.transactions:
        assert args.node != "polygon", "Transactions are not supported for Polygon"
        execute_txs(controller, args.transactions)
        sys.exit() 
    if args.benchmark == "transfers":
        benchmark_transfers(controller, addresses, args.timeout)
    elif args.benchmark == "erc20":
        benchmark_erc20(controller, addresses, args.timeout)
    elif args.benchmark == "deploy":
        benchmark_deploy(controller, addresses, args.timeout)
    elif args.benchmark == "sha256":
        benchmark_sha256(controller, addresses, args.timeout, "contracts/SHA256.sol", "SHA256")
    elif args.benchmark == "precompilesha256":
        benchmark_sha256(controller, addresses, args.timeout, "contracts/KeccakPrecompile.sol", "KeccakPrecompile")
    elif args.benchmark == "maxethtransfers":
        benchmark_transfers_max(controller, addresses, args.timeout)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--node', choices=["geth", "zksync", "polygon"], required=True)
    parser.add_argument('--transactions')
    parser.add_argument('--benchmark', choices=["transfers", "erc20", "deploy", "sha256", "precompilesha256", "maxethtransfers"])
    # Addresses are pk, address
    parser.add_argument('--addresses', default="addresses.csv")
    parser.add_argument('--timeout', default=180, type=int)
    args = parser.parse_args()
    assert args.transactions or args.benchmark
    assert not (args.transactions and args.benchmark)
    main(args)