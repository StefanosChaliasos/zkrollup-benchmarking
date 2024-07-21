#!/bin/bash

# Function to print usage
usage() {
  echo "Usage: $0 <polygon_zkevm_dir> <polygon_testvectors> <benchmark_inputs_dir> <test>"
  exit 1
}

# Check if the correct number of arguments is provided
if [ "$#" -ne 4 ]; then
  usage
fi

# Read arguments
polygon_zkevm_dir=$1
polygon_testvectors=$2
benchmark_inputs_dir=$3
test=$4

# Ensure paths are absolute
if [[ "$polygon_zkevm_dir" != /* ]]; then
  echo "Error: polygon_zkevm_dir must be an absolute path."
  exit 1
fi

if [[ "$polygon_testvectors" != /* ]]; then
  echo "Error: polygon_testvectors must be an absolute path."
  exit 1
fi

if [[ "$benchmark_inputs_dir" != /* ]]; then
  echo "Error: benchmark_inputs_dir must be an absolute path."
  exit 1
fi

# Save the current directory
INIT_DIR=$(pwd)

# Create log directory
LOGS="$INIT_DIR/polygon_logs/logs_$test"
mkdir -p "$LOGS"

# List files in benchmark_inputs_dir
listOfFiles=$(ls "$benchmark_inputs_dir")

# Print paths at the start
echo "polygon_zkevm_dir: $polygon_zkevm_dir"
echo "polygon_testvectors: $polygon_testvectors"
echo "benchmark_inputs_dir: $benchmark_inputs_dir"
echo "test: $test"
echo "INIT_DIR: $INIT_DIR"
echo "LOGS directory: $LOGS"
echo "Files in $benchmark_inputs_dir:"
echo "$listOfFiles"

# Save the paths to a log file for reference
echo "polygon_zkevm_dir: $polygon_zkevm_dir" >> "$LOGS/paths.log"
echo "polygon_testvectors: $polygon_testvectors" >> "$LOGS/paths.log"
echo "benchmark_inputs_dir: $benchmark_inputs_dir" >> "$LOGS/paths.log"
echo "test: $test" >> "$LOGS/paths.log"
echo "INIT_DIR: $INIT_DIR" >> "$LOGS/paths.log"
echo "LOGS directory: $LOGS" >> "$LOGS/paths.log"
echo "Files in $benchmark_inputs_dir:" >> "$LOGS/paths.log"
echo "$listOfFiles" >> "$LOGS/paths.log"

# Process each file in the benchmark inputs directory
touch ${polygon_zkevm_dir}/benchmarks_${test}.csv
for file in $listOfFiles; do
    echo "Processing file: $file"
    echo "Copying file to zkevm-testvectors"
    cp "$benchmark_inputs_dir/$file" "$polygon_testvectors/tools-inputs/tools-calldata/generate-test-vectors/gen-$file"
    
    cd "$polygon_testvectors"
    echo "(1/2) Generating inputs for file: $file"
    npx mocha --max-old-space-size=524288 tools-inputs/tools-calldata/gen-test-vectors-evm.js --vectors "gen-$file"
    echo "(2/2) Generating inputs for file: $file"
    npx mocha --max-old-space-size=524288 tools-inputs/generators/calldata-gen-inputs.js --timeout 0 --vectors "$file" --update --output --evm-debug

    fileWithoutExtension="${file%.*}"
    echo $fileWithoutExtension
    echo "Copying generated files to testvectors"
    fileOutput="${fileWithoutExtension}_0.json"
    cp "$polygon_testvectors/inputs-executor/calldata/$fileOutput" "$polygon_zkevm_dir/testvectors/e2e/fork_9/input_executor_0.json"
    
    cd "$polygon_zkevm_dir"
    csv_file="benchmarks.csv"
    
    echo "Running prover"
    BENCH_BATCH=1 time build/zkProver -c testvectors/config_runFile_e2e.json >> "$LOGS/$fileWithoutExtension.log" 2>&1
    echo "Prover done"
    echo
    echo "Writing file name to csv"
    sed -e '$s/^/'"$fileWithoutExtension"',/' benchmarks.csv > temp && mv temp benchmarks.csv
    echo "" >> benchmarks.csv
    echo "Moving files to backup"
    mkdir -p "testvectors/e2e/fork_9/$fileWithoutExtension"
    mv "testvectors/e2e/fork_9/"*.json "testvectors/e2e/fork_9/$fileWithoutExtension"

    mkdir -p "runtime/output/$fileWithoutExtension"
    mv "runtime/output/"*.json "runtime/output/$fileWithoutExtension"
    
    echo "Done processing file: $file"
    echo
    echo
done

mv benchmarks.csv "benchmarks_$test.csv"
