#!/usr/bin/env python3.6

"""
Cluster together probes belonging to tokens that share similar SSID sets.
An optimal clustering is such that every token in a cluster belongs
to the same MAC address. AND every token has been clustered.
"""

__author__ = "Richard Cosgrove"
__license__ = "MIT"

from collections import defaultdict, Counter
import csv
import decimal
from functools import partial
from itertools import combinations
from pprint import pprint
import pickle
import multiprocessing
import sys

# Local imports
from utilities import import_compressed_json
from utilities import validate_clusters, match_tokens_with_same_ssid_set

def filter_false_pos_tokens_from_cluster(token_to_probes, cluster):
    """ Remove any token from a cluster that does not have the most common fingerprint.
    :param token_to_probes: Dictionary of token to list of probe dictionary
    :param cluster: set of tokens
    """
    token_to_fingerprint = {}

    # First match each token to its probe's fingerprints
    for token in cluster:
        fingerprints = set()
        fingerprints |= {probe["fingerprint"] for probe in token_to_probes[token]}

        # We only care about a token if its fingerprint is stable
        # i.e. it does not change.
        if len(fingerprints) == 1:
            token_to_fingerprint[token] = fingerprints.pop()

    if not token_to_fingerprint:
        # Do nothing - no token has a stable fingerprint
        return cluster

    # Now remove any token whose fingerprint is not consistent with the
    # most common fingerprint.
    most_common_fingerprint = Counter(token_to_fingerprint.values()).most_common(1)[0][0]

    return cluster - {token for token in token_to_fingerprint.keys() 
           if token_to_fingerprint[token] != most_common_fingerprint}

def cluster(token_to_probes, ssid_set_to_tokens, ssid_set_to_matches, 
            token_to_ssid_set, check_fingerprints):
    """
    :param token_to_probes: Dictionary of token to list of probe dictionary
    :param ssid_set_to_tokens: Dictionary of SSID set to set of tokens
    :param ssid_set_to_matches: Dictionary of SSID set to set of SSID set
    :param token_to_ssid_set: Dictionary of token to SSID set
    :yields: a cluster upon one being generated
    """
    tokens_remaining = set(token_to_ssid_set.keys())

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

            # Get SSID set belonging to token
            ssid_set = token_to_ssid_set[token]

            # Get tokens with the same SSID set that have not yet been clustered
            tokens_to_match |= {token 
                                for token in ssid_set_to_tokens[ssid_set] 
                                if token in tokens_remaining
            }
            
            # Get SSID sets "similar" to this SSID set
            similar_ssid_sets = ssid_set_to_matches[ssid_set]

            # Get tokens with similar SSID set that have not yet been clustered
            tokens_to_match |= {token 
                                for matched_ssid_set in similar_ssid_sets 
                                for token in ssid_set_to_tokens[matched_ssid_set] 
                                if token in tokens_remaining
            }

        if check_fingerprints:
            cluster = filter_false_pos_tokens_from_cluster(token_to_probes, cluster)

        yield cluster

def jaccard_worker(chunk, threshold):
    intersection_cardinality = len(chunk[0].intersection(chunk[1]))
    union_cardinality = len(chunk[0]) + len(chunk[1]) - intersection_cardinality
    if intersection_cardinality / float(union_cardinality) >= threshold:
        return chunk

def single_processor_get_similar_ssid_sets(ssid_sets, threshold):
    ssid_set_to_matches = defaultdict(set)
    ssid_pairs = combinations(ssid_sets, r=2)
    for pair in ssid_pairs:
        match = jaccard_worker(pair, threshold)
        if match:
            ssid_set_to_matches[match[0]].add(match[1])
            ssid_set_to_matches[match[1]].add(match[0])
    return ssid_set_to_matches

def get_similar_ssid_sets(ssid_sets, threshold):
    """Return a mapping of ssid set to similar ssid sets.
    :param ssid_sets: Iterable of SSID sets
    :param threshold: Minimum Jaccard index for two sets to be matched as similar.
    """
    ssid_set_to_matches = defaultdict(set)
    ssid_pairs = combinations(ssid_sets, r=2)

    # Distribute calulcations to worker processes
    # Significant speed-up over single process
    with multiprocessing.Pool() as pool:
        task = partial(jaccard_worker, threshold=threshold)

        # Immediately returns an iterable
        similar_ssids = pool.imap_unordered(task, ssid_pairs, chunksize=300000)

        # Consumes the iterable whenever a worker process yields
        for match in similar_ssids:
            if match:
                ssid_set_to_matches[match[0]].add(match[1])
                ssid_set_to_matches[match[1]].add(match[0])

    return ssid_set_to_matches

def cluster_with_threshold(token_to_probes, threshold, check_fingerprints):
    """
    :param token_to_probes: Dictionary of token to list of probe dictionary
    :param threshold: Minimum Jaccard index for two sets to be matched as similar.
    :param check_fingerprints: Optional step to remove false positives.
    :returns: Dictionary of binary classification results (true pos, false pos, etc.)
    """
    print("Matching tokens with the same SSID set.")
    ssid_set_to_tokens, token_to_ssid_set = match_tokens_with_same_ssid_set(token_to_probes)

    print("Matching SSID sets with a Jaccard similarity index greater than", threshold)
    # ssid_set_to_matches = get_similar_ssid_sets(ssid_set_to_tokens.keys(), threshold)
    ssid_set_to_matches = single_processor_get_similar_ssid_sets(ssid_set_to_tokens.keys(), threshold)
    
    print("Clustering tokens with similar SSID sets.")
    clusters = cluster(token_to_probes, ssid_set_to_tokens, ssid_set_to_matches, 
                       token_to_ssid_set, check_fingerprints)

    if check_fingerprints:
        print("Filtering false positive matchings from cluster by comparing device fingerprints.")

    return validate_clusters(clusters, token_to_probes)

def write_results_at_various_thresholds(token_to_probes, check_fingerprints, increment_threshold_by=0.01):
    """Output to CSV results at various thresholds. Used to draw ROC curve.
    :param token_to_probes: Dictionary of token to list of probe dictionary
    :param check_fingerprints: Optional step to remove false positives.
    """
    def drange(x, y, jump):
        """Because python doesn't support decimal steps..."""
        while x <= y:
            yield float(x)
            x += decimal.Decimal(jump)

    with open("jaccard_threshold_results.csv", "w") as f:
        writer = csv.DictWriter(f, fieldnames=["tp", "fp", "tn", "fn", "tpr", "fpr", "accuracy", "clusters", "macs", "median"])
        writer.writeheader()
        for threshold in drange(0, 1.01, increment_threshold_by):
            writer.writerow(cluster_with_threshold(token_to_probes, threshold, check_fingerprints))

def main(test_various_thresholds=False, check_fingerprints=False):
    """Cluster with default similarity threshold.
    :param test_various_thresholds: Flag to be used when generating CSV for ROC curve.
    :param check_fingerprints: Optional step to remove false positives.
    """
    if check_fingerprints:
        token_to_probes = import_compressed_json("int/token_to_probe_inc_fingerprint.json.gz")
    else:
        token_to_probes = import_compressed_json("int/token_to_probe.json.gz")

    if test_various_thresholds:
        write_results_at_various_thresholds(token_to_probes, check_fingerprints)
    else:
        # Use optimal threshold
        results = cluster_with_threshold(token_to_probes, 0.67, check_fingerprints)
        pprint(results)
        return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", help="Generate CSV of results at various thresholds.",
                        action="store_true")
    parser.add_argument("--fingerprint", help="Check clusters against fingerprints.",
                        action="store_true")
    args = parser.parse_args()
    main(test_various_thresholds=args.csv, check_fingerprints=args.fingerprint)
