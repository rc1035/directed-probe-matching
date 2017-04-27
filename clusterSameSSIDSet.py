#!/usr/bin/env python3.6

"""
Cluster together tokens that share the SSID set.
An optimal clustering is such that every token in a cluster belongs
to the same MAC address. AND every token has been clustered.
"""

__author__ = "Richard Cosgrove"

from collections import defaultdict
from pprint import pprint

# Local imports
from utilities import import_compressed_json
from utilities import validate_clusters, match_tokens_with_same_ssid_set

def main():
    token_to_probes = import_compressed_json("int/token_to_probe.json.gz")

    # Matching to be used for clustering.
    print("Matching tokens with the same SSID set.")
    ssid_set_to_tokens, _ = match_tokens_with_same_ssid_set(token_to_probes)

    # Validate generated clusters.
    print("Validating clusters...")
    results = validate_clusters(ssid_set_to_tokens.values(), token_to_probes)
    pprint(results)

    return results

if __name__ == "__main__":
    main()
