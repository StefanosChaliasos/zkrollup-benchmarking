import argparse
import json
import psycopg2
from sshtunnel import SSHTunnelForwarder
import pandas as pd

def parse_arguments():
    parser = argparse.ArgumentParser(description='Connect to PostgreSQL databases through SSH tunnel')
    parser.add_argument('--ssh-username', required=True, help='SSH username')
    parser.add_argument('--ssh-host', required=True, help='SSH host')
    parser.add_argument('--ssh-port', type=int, default=22, help='SSH port')
    parser.add_argument('--ssh-key', required=True, help='Path to SSH private key')
    parser.add_argument('--db-password', required=True, help='PostgreSQL database password')
    parser.add_argument('--json-file', required=True, help='Path to JSON file')
    parser.add_argument('--output-file', required=True, help='Path to output CSV file')
    return parser.parse_args()

def connect_to_db(dbname, port, db_password):
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user='postgres',
            password=db_password,
            host='localhost',
            port=port
        )
        print(f"Successfully connected to database {dbname} on port {port}")
        return conn
    except Exception as e:
        print(f"Failed to connect to database {dbname}: {e}")
        return None

def load_json(filepath):
    with open(filepath, 'r') as file:
        return json.load(file)

def time_to_seconds(time_obj):
    return time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second

def get_time_taken_sum(conn, table, column, batch_number):
    cursor = conn.cursor()
    cursor.execute(f"SELECT time_taken FROM {table} WHERE {column} = %s", (batch_number,))
    results = cursor.fetchall()
    cursor.close()
    return sum(time_to_seconds(row[0]) for row in results)

def get_compressed_state_diffs_size(conn, batch_number):
    cursor = conn.cursor()
    cursor.execute(f"SELECT pubdata_input FROM l1_batches WHERE number = %s", (batch_number,))
    result = cursor.fetchone()
    cursor.close()
    if result and result[0]:
        return len(bytes(result[0]))
    return 0

def main():
    args = parse_arguments()

    with SSHTunnelForwarder(
        (args.ssh_host, args.ssh_port),
        ssh_username=args.ssh_username,
        ssh_pkey=args.ssh_key,
        remote_bind_addresses=[('localhost', 5432), ('localhost', 5432)],
        local_bind_addresses=[('localhost', 6543), ('localhost', 6544)]
    ) as tunnel:
        print("SSH tunnel established")

        # Connect to the databases
        conn_zksync = connect_to_db('zksync_local', 6543, args.db_password)
        conn_prover = connect_to_db('prover_local', 6544, args.db_password)

        if not conn_zksync or not conn_prover:
            print("Failed to connect to one or more databases, exiting...")
            return
        
        # Load and parse the JSON file
        data = load_json(args.json_file)

        # Prepare to store results
        results = []

        # Compute states for each batch
        for item in data:
            batch_number = int(item['Batch Number'])
            title = item['Title']
            input_value = title.split('_')[0]  # Extract input value correctly
            payload = '_'.join(title.split('_')[1:])  # Extract payload correctly
            
            # Compute witness time
            witness_time_inputs = get_time_taken_sum(conn_prover, 'witness_inputs_fri', 'l1_batch_number', batch_number)
            witness_time_scheduler = get_time_taken_sum(conn_prover, 'scheduler_witness_jobs_fri', 'l1_batch_number', batch_number)
            witness_time = witness_time_inputs + witness_time_scheduler
            
            # Compute proving time
            proving_time_prover = get_time_taken_sum(conn_prover, 'prover_jobs_fri', 'l1_batch_number', batch_number)
            proving_time_node = get_time_taken_sum(conn_prover, 'node_aggregation_witness_jobs_fri', 'l1_batch_number', batch_number)
            proving_time_leaf = get_time_taken_sum(conn_prover, 'leaf_aggregation_witness_jobs_fri', 'l1_batch_number', batch_number)
            proving_time = proving_time_prover + proving_time_node + proving_time_leaf
            
            # Combine witness and proving time
            witness_and_proving_time = witness_time + proving_time
            
            # Get compressed_state_diffs size in bytes
            compressed_state_diffs_size = get_compressed_state_diffs_size(conn_zksync, batch_number)
            
            # Append results for Proving Time
            results.append({
                'payload': payload,
                'input': input_value,
                'metric': 'Proving Time',
                'value': witness_and_proving_time
            })
            
            # Append results for DA Bytes
            results.append({
                'payload': payload,
                'input': input_value,
                'metric': 'DA Bytes',
                'value': compressed_state_diffs_size
            })

        # Close the connections
        conn_zksync.close()
        conn_prover.close()

        # Convert results to a DataFrame
        df = pd.DataFrame(results)

        # Output the dataframe to a CSV file
        df.to_csv(args.output_file, index=False)

if __name__ == '__main__':
    main()
