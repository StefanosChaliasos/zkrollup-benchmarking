import argparse
import csv
import secrets
from eth_account import Account


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--addresses', default=100, type=int)
    parser.add_argument('--filename', default="wallets.csv")
    args = parser.parse_args()
    num_addresses = args.addresses
    filename = args.filename

    # Generate and save addresses
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)

        for _ in range(num_addresses):
            # Generate a new account
            priv = secrets.token_hex(32)
            private_key = "0x" + priv
            account = Account.from_key(private_key)
            
            # Write the private key and address to the CSV
            writer.writerow([private_key, account.address])

    print(f"Generated {num_addresses} Ethereum addresses and private keys in {filename}")

if __name__ == "__main__":
    main()
