#!/usr/bin/env python3.6

"""
Cluster together probes belonging to tokens that share n-tuples of SSID sets.
An optimal clustering is such that every token in a cluster belongs
to the same MAC address. AND every token has been clustered.
"""

__author__ = "Richard Cosgrove"
__license__ = "MIT"

import csv
from collections import defaultdict
from pprint import pprint

# Local imports
from utilities import import_compressed_json
from utilities import validate_clusters, match_tokens_with_same_ssid_set

def cluster(ssid_tuple_to_tokens, token_to_ssid_tuples):
    """
    :param ssid_tuple_to_tokens: Dictionary of SSID tuple to set of tokens
    :param token_to_ssid_tuple: Dictionary of token to SSID tuples
    :yields: a cluster upon one being generated
    """
    tokens_remaining = set(token_to_ssid_tuples.keys())
    sanity_count = len(tokens_remaining)
    while tokens_remaining:
        cluster = set()
        tokens_to_match = set()

        # Start cluster with arbitrary token
        start_token = tokens_remaining.pop()
        tokens_to_match.add(start_token)

        # Keep looping until no more tokens can be found on stack
        # This is much faster than recursion
        while tokens_to_match:

            # Add token to cluster and remove from tokens_to_match stack
            token = tokens_to_match.pop()
            cluster.add(token)
            tokens_remaining.discard(token)

            # Get tokens with the same SSID tuples that have not yet been clustered
            tokens_to_match |= {token 
                                for ssid_tuple in token_to_ssid_tuples[token] 
                                for token in ssid_tuple_to_tokens[ssid_tuple] 
                                if token in tokens_remaining
            }

        sanity_count -= len(cluster)
        yield cluster

    assert(sanity_count == 0)

def match_tokens_with_shared_ordered_ssid_tuple(token_to_probes, n):
    ssid_tuple_to_tokens = defaultdict(set)
    token_to_ssid_tuples = defaultdict(set)
    for token, probes in token_to_probes.items():

        ssid_list = []

        for probe in probes:
            if probe["ssid"] == 0 or (len(ssid_list) and ssid_list[-1] == probe["ssid"]):
                # Ignore broadcast probes.
                continue
            ssid_list.append(probe["ssid"])

        # SSID set smaller than minimum n-tuple size
        if len(ssid_list) < n:
            continue

        # Fingerprint every ordered n-tuple of SSIDs
        for i in range(len(ssid_list) - (n-1)):
            sub = ssid_list[i:i+n]
            assert len(sub) == n
            ssid_tuple_to_tokens[tuple(sub)].add(token)
            token_to_ssid_tuples[token].add(tuple(sub))

    return (ssid_tuple_to_tokens, token_to_ssid_tuples)

def write_results_at_various_thresholds(token_to_probes):
    """Output to CSV results at various thresholds. Used to draw ROC curve.
    :param token_to_probes: Dictionary of token to list of probe dictionary
    """
    with open("n_value_results.csv", "w") as f:
        writer = csv.DictWriter(f, fieldnames=["tp", "fp", "tn", "fn", "tpr", "fpr", "accuracy", "clusters", "macs", "median"])
        writer.writeheader()
        for n in range(2, 30):
            print(n)
            ssid_tuple_to_tokens, token_to_ssid_tuples = match_tokens_with_shared_ordered_ssid_tuple(token_to_probes, n)
            writer.writerow(validate_clusters(cluster(ssid_tuple_to_tokens, token_to_ssid_tuples), token_to_probes))

def main(n=6):
    token_to_probes = import_compressed_json("int/token_to_probe.json.gz")

    # Matching to be used for clustering.
    print("Matching tokens sharing %i-tuples of SSIDs." % (n,))
    ssid_tuple_to_tokens, token_to_ssid_tuples = match_tokens_with_shared_ordered_ssid_tuple(token_to_probes, n)

    print("Clustering tokens with shared %i-tuples of SSIDs." % (n,))
    results = validate_clusters(cluster(ssid_tuple_to_tokens, token_to_ssid_tuples), token_to_probes)
    pprint(results)

if __name__ == "__main__":
    main()
