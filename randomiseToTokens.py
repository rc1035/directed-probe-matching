#!/usr/bin/env python3.6

"""Import JSON exported by parsePackets.py and apply MAC Address Randomisation."""

__author__ = "Richard Cosgrove"
__license__ = "MIT"

from collections import defaultdict
from datetime import datetime, timedelta
from itertools import combinations

# Local imports
from utilities import import_compressed_json, export_compressed_json

# Hardcoded: Very first timestamp in dataSet.
EPOCH_DATETIME = datetime(2013, 3, 28, 17, 53, 46)

def randomise(mac_to_probe, randomisation_interval):
    print("Applying MAC randomisation to probes.")
    token = 0

    # To be used for clustering.
    token_to_probe = defaultdict(list)

    # To be used to validate clusters (see utilities.py).
    token_to_mac = {}

    for mac_address, probes in mac_to_probe.items():

        start_time = EPOCH_DATETIME + timedelta(seconds=float(probes[0]["timestamp"]))

        # New MAC Address -> New token
        token += 1
        token_to_mac[token] = mac_address

        for probe in probes:
            new_time = EPOCH_DATETIME + timedelta(seconds=float(probe["timestamp"]))

            if new_time - start_time > randomisation_interval:

                # Exceeded MAX delta between packets -> New token
                token += 1
                token_to_mac[token] = mac_address

                start_time = new_time

            token_to_probe[token].append(probe)
    
    assert(len(token_to_probe.keys()) == len(token_to_mac.keys()))

    print("Tokens total:", token)
    return (token_to_probe, token_to_mac)

def calculate_valid_combinations(token_to_mac, token_to_probe):
    print("Calculating valid pairs of tokens...")
    valid_pairs = 0

    # We only care about tokens that probe for SSIDs
    for token, probes in token_to_probe.items():
        uses_directed_probes = False
        for probe in probes:
            if probe["ssid"] != 0:
                uses_directed_probes = True

        if not uses_directed_probes:
            del token_to_mac[token]

    # Group by MAC
    mac_to_tokens = defaultdict(set)
    for token, mac in token_to_mac.items():
        mac_to_tokens[mac].add(token)

    print("MACs sending directed probes:", len(mac_to_tokens.keys()))

    # Count number of token pairs in this group
    for _, tokens in mac_to_tokens.items():
        valid_pairs += len(list(combinations(tokens, r=2)))

    num_of_tokens = len(list(token_to_mac.keys()))
    total_pairs = int(((num_of_tokens) * (num_of_tokens-1)) / 2)
    invalid_pairs = total_pairs - valid_pairs

    print("Tokens sending directed probes:", num_of_tokens)
    print("Total pairs: ", total_pairs)
    print("Valid pairs:", valid_pairs)
    print("Invalid pairs:", invalid_pairs)

    return {
    "total_pairs": total_pairs, 
    "valid_pairs": valid_pairs, 
    "invalid_pairs": invalid_pairs
    }

def main(include_fingerprints, randomisation_interval=timedelta(hours=12)):
    """Convert MAC Address to token with default randomisation interval."""
    if include_fingerprints:
        mac_to_probe = import_compressed_json("int/mac_to_probe_inc_fingerprint.json.gz")
    else:
        mac_to_probe = import_compressed_json("int/mac_to_probe.json.gz")
    
    token_to_probe, token_to_mac = randomise(mac_to_probe, randomisation_interval)

    if include_fingerprints:
        export_compressed_json(token_to_probe, "int/token_to_probe_inc_fingerprint.json.gz")
    else:
        export_compressed_json(token_to_probe, "int/token_to_probe.json.gz")
    
    export_compressed_json(token_to_mac, "int/token_to_mac.json.gz")
    export_compressed_json(calculate_valid_combinations(token_to_mac, token_to_probe), "int/valid_combinations.json.gz")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--fingerprint", help="Include fingerprint (much slower).",
                        action="store_true")
    args = parser.parse_args()
    main(include_fingerprints=args.fingerprint)