#!/usr/bin/env python3.6

"""Refactored utility functions."""

__author__ = "Richard Cosgrove"

from collections import defaultdict
import gzip
from itertools import combinations
from datetime import datetime, timedelta
import json
import os

def export_compressed_json(dict_item, file_name):
    """Export gzip compressed JSON.
    (For Uni dataset compressed size is ~10% of uncompressed.)
    :param dict_item: Dictionary to dump as JSON.
    :param file_name: Name of file to be written e.g. dict.json.gz
    """
    # Use lowest level of compression for fast speed.
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    with gzip.open(file_name, mode="wt", compresslevel=1) as f:
        json.dump(dict_item, f, separators=(',', ':'))

def import_compressed_json(file_name):
    """Import gzip compressed JSON.
    :param file_name: Name of file to be read e.g. dict.json.gz
    :returns: JSON as a dictionary.
    """
    with gzip.open(file_name, mode="rt") as f:
        return json.load(f)

def match_tokens_with_same_ssid_set(token_to_probes):
    """Split into clusters that share the SAME set of SSIDs probed for.
    :param token_to_probes: Dictionary with token keys and probe values
    :returns: Dictionary with SSID set keys and token values
    """
    ssid_set_to_tokens = defaultdict(set)
    token_to_ssid_set = {}
    for token, probes in token_to_probes.items():

        ssid_set = set()

        for probe in probes:
            if probe["ssid"] == 0:
                # Ignore broadcast probes.
                continue
            ssid_set.add(probe["ssid"])

        if len(ssid_set) < 2:
            # Ignore sets with cardinality less than X
            # due to high rate of false positives.
            continue

        # Cluster token with any tokens that share the same SSID set.
        ssid_set_to_tokens[frozenset(ssid_set)].add(token)
        token_to_ssid_set[token] = frozenset(ssid_set)

    # Sanity check: Assert that no token has been matched more than once.
    tokens = [t for tokens in list(ssid_set_to_tokens.values()) for t in tokens]
    assert(len(tokens) == len(set(tokens)))

    return (ssid_set_to_tokens, token_to_ssid_set)

def validate_clusters(clusters, token_to_probes):
    """Validate the correctness of a clustering.
    :param clusters: An iterable of clusters, where each cluster is a list of tokens.
    :returns: Dictionary of binary classifier results
    """
    token_to_mac = import_compressed_json("int/token_to_mac.json.gz")
    
    # Use a binary Classification
    true_positives, false_positives = 0, 0
    num_of_clusters = 0

    mac_to_timestamps = defaultdict(list)

    for cluster in clusters:

        num_of_clusters += 1
        for pair in combinations(cluster, r=2):
            if token_to_mac[pair[0]] == token_to_mac[pair[1]]:
                true_positives += 1

                mac = token_to_mac[pair[0]]
                t1_timestamps = [float(p["timestamp"]) for p in token_to_probes[pair[0]]]
                t2_timestamps = [float(p["timestamp"]) for p in token_to_probes[pair[1]]]
                mac_to_timestamps[mac] += t1_timestamps
                mac_to_timestamps[mac] += t2_timestamps

            else:
                false_positives += 1

    greater_than = 0
    lengths = []
    for mac, timestamps in mac_to_timestamps.items():
        length = timedelta(seconds=max(timestamps)) - timedelta(seconds=min(timestamps))
        if length > timedelta(hours=12):
            greater_than += 1
            lengths.append(length)

    import statistics
    mid = statistics.median(lengths)

    # Total number of valid pairs and invalid pairs have been
    # pre-computed in randomiseTokens.py ...
    # So we can easily calculate the negatives by subtracting the positives.
    actual_combos = import_compressed_json("int/valid_combinations.json.gz")
    true_negatives = actual_combos["invalid_pairs"] - false_positives
    false_negatives = actual_combos["valid_pairs"] - true_positives

    # Sanity checks
    assert(true_positives + false_positives +  true_negatives + false_negatives == actual_combos["total_pairs"])
    assert(true_positives + false_negatives == actual_combos["valid_pairs"])
    assert(false_positives + true_negatives == actual_combos["invalid_pairs"])

    true_positive_rate = (true_positives / (float(true_positives + false_negatives)))
    false_positive_rate = (false_positives / (float(false_positives + true_negatives)))
    accuracy = (true_positives + true_negatives) / float(actual_combos["total_pairs"])

    return {
        "tp": true_positives,
        "fp": false_positives,
        "tn": true_negatives,
        "fn": false_negatives,
        "tpr": true_positive_rate,
        "fpr": false_positive_rate,
        "accuracy": accuracy,
        "clusters": num_of_clusters,
        "macs": greater_than,
        "median": mid
    }
