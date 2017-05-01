import unittest
from datetime import datetime, timedelta

# Modules to test
import utilities
import randomiseToTokens
import clusterSimilarSSIDSets
import clusterOrderedSSIDSets

# Test data

MACS_TO_PROBES = {"MAC_ONE": [{"timestamp": 531, "ssid": 5}], 
                  "MAC_TWO": [{"timestamp": 242, "ssid": 5}, {"timestamp": 643, "ssid": 9},
                              {"timestamp": 999999995, "ssid": 5}, {"timestamp": 999999999, "ssid": 9}
                              ],
                  "MAC_THREE": [{"timestamp": 264, "ssid": 5}, {"timestamp": 895, "ssid": 16}]}

TOKENS_TO_PROBES = {1: [{"timestamp": 531, "ssid": 5}], 
                    2: [{"timestamp": 242, "ssid": 5}, {"timestamp": 643, "ssid": 9}], 
                    3: [{"timestamp": 999999995, "ssid": 5}, {"timestamp": 999999999, "ssid": 9}],
                    4: [{"timestamp": 264, "ssid": 5}, {"timestamp": 895, "ssid": 16}]}

CLUSTERS = [[1], [2,3], [4]]

TOKEN_TO_MAC = {1: "MAC_ONE", 2: "MAC_TWO", 3: "MAC_TWO", 4: "MAC_THREE"}

VALID_COMBINATIONS = {"total_pairs":6, "valid_pairs":1, "invalid_pairs":5}

# Monkey patch import function to use test data, and export to do nothing.
def import_compressed_json(file_name):
    if "int/token_to_mac.json.gz" == file_name:
        return TOKEN_TO_MAC
    elif "int/valid_combinations.json.gz" == file_name:
        return VALID_COMBINATIONS

def export_compressed_json(dict_item, file_name):
    pass

# Tests

class TestUtilityMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        utilities.import_compressed_json = import_compressed_json

    def test_token_matching(self):
        ssid_set_to_tokens, token_to_ssid_set = utilities.match_tokens_with_same_ssid_set(TOKENS_TO_PROBES)

        # SSID sets to tokens
        self.assertEqual(len(ssid_set_to_tokens.keys()), 2)
        self.assertEqual(ssid_set_to_tokens[frozenset({5,9})], {2,3})
        self.assertEqual(ssid_set_to_tokens[frozenset({5,16})], {4})

        # Token to SSID sets
        self.assertEqual(len(token_to_ssid_set.keys()), 3)
        self.assertEqual(token_to_ssid_set[2], {5,9})
        self.assertEqual(token_to_ssid_set[4], {5,16})

    def test_validate_clusters_no_false_pos(self):
        results = utilities.validate_clusters(CLUSTERS, TOKENS_TO_PROBES)
        self.assertEqual(results["tp"], 1)
        self.assertEqual(results["fp"], 0)
        self.assertEqual(results["tn"], 5)
        self.assertEqual(results["fn"], 0)
        self.assertEqual(results["tpr"], 1.0)
        self.assertEqual(results["fpr"], 0.0)
        self.assertEqual(results["accuracy"], 1.0)
        self.assertEqual(results["clusters"], len(CLUSTERS))
        # 1 MAC with duration > 12 hours
        self.assertEqual(results["macs"], 1)

    def test_validate_clusters_with_false_pos(self):
        # False pos - matching 3 and 4
        bad_cluster = [[1], [2,3], [3,4]]
        results = utilities.validate_clusters(bad_cluster, TOKENS_TO_PROBES)
        self.assertEqual(results["tp"], 1)
        self.assertEqual(results["fp"], 1)
        self.assertEqual(results["tn"], 4)
        self.assertEqual(results["fn"], 0)

    def test_validate_clusters_with_false_neg(self):
        # False pos - matching 3 and 4
        bad_cluster = [[1], [2], [3], [4]]
        results = utilities.validate_clusters(bad_cluster, TOKENS_TO_PROBES)
        self.assertEqual(results["tp"], 0)
        self.assertEqual(results["fp"], 0)
        self.assertEqual(results["tn"], 5)
        self.assertEqual(results["fn"], 1)


flatten = lambda l: [item for sublist in l for item in sublist]

class TestRandomiseMethods(unittest.TestCase):

    def test_randomise_macs(self):
        token_to_probe, token_to_mac = randomiseToTokens.randomise(MACS_TO_PROBES, timedelta(hours=12))
        self.assertEqual(token_to_probe, TOKENS_TO_PROBES)
        self.assertEqual(token_to_mac, TOKEN_TO_MAC)

    def test_randomise_macs_second_interval(self):
        token_to_probe, token_to_mac = randomiseToTokens.randomise(MACS_TO_PROBES, timedelta(seconds=1))
        self.assertEqual(list(token_to_probe.keys()), [1,2,3,4,5,6,7])
        self.assertEqual(flatten(list(token_to_probe.values())), flatten(list(MACS_TO_PROBES.values())))
        self.assertEqual(token_to_mac[1], "MAC_ONE")
        self.assertEqual(token_to_mac[3], "MAC_TWO")


setA = frozenset({1,2,3,4})
setB = frozenset({1,2,3,4,5})
setC = frozenset({1,6,7,8,9})

class TestSimilarSSIDMethods(unittest.TestCase):

    def test_similar_ssid_set_one(self):
        """Sets that share at least half elements in common."""
        ssid_set_to_matches = clusterSimilarSSIDSets.get_similar_ssid_sets([setA, setB, setC], 0.5)
        self.assertEqual(len(ssid_set_to_matches), 2)
        self.assertEqual(ssid_set_to_matches[setA], {setB})
        self.assertEqual(ssid_set_to_matches[setB], {setA})

    def test_similar_ssid_set_two(self):
        """Sets that share at least no elements in common."""
        ssid_set_to_matches = clusterSimilarSSIDSets.get_similar_ssid_sets([setA, setB, setC], 0)
        self.assertEqual(len(ssid_set_to_matches), 3)
        self.assertEqual(ssid_set_to_matches[setA], {setB, setC})
        self.assertEqual(ssid_set_to_matches[setB], {setA, setC})
        self.assertEqual(ssid_set_to_matches[setC], {setA, setB})

    def test_similar_ssid_set_three(self):
        """Sets that share all elements in common i.e. are the same"""
        ssid_set_to_matches = clusterSimilarSSIDSets.get_similar_ssid_sets([setA, setB, setC], 1)
        self.assertEqual(len(ssid_set_to_matches), 0)

        setD = frozenset({1,6,7,8,9})
        ssid_set_to_matches = clusterSimilarSSIDSets.get_similar_ssid_sets([setA, setB, setC, setD], 1)
        self.assertEqual(len(ssid_set_to_matches), 1)
        self.assertEqual(ssid_set_to_matches[setC], {setD})
        self.assertEqual(ssid_set_to_matches[setD], {setC})


class TestOrderedTupleMatchingMethods(unittest.TestCase):

    def test_match_tokens_with_shared_tuple(self):
        ssid_tuple_to_tokens, token_to_ssid_tuples = clusterOrderedSSIDSets.match_tokens_with_shared_ordered_ssid_tuple(
                                                        TOKENS_TO_PROBES, 2)
        self.assertEqual(len(ssid_tuple_to_tokens), 2)
        self.assertEqual(ssid_tuple_to_tokens[(5,9)], {2,3})
        self.assertEqual(ssid_tuple_to_tokens[(5,16)], {4})
        self.assertEqual(len(token_to_ssid_tuples), 3)
        self.assertEqual(token_to_ssid_tuples[2], {(5,9)})
        self.assertEqual(token_to_ssid_tuples[3], {(5,9)})
        self.assertEqual(token_to_ssid_tuples[4], {(5,16)})


class TestClusteringMethods(unittest.TestCase):
    
    def test_cluster_similar(self):
        ssid_set_to_tokens = {frozenset({5,9}): {2,3}, frozenset({5,16}): {4}}
        ssid_set_to_matches = {frozenset({5,9}): {frozenset({5,16})}, frozenset({5,16}): {frozenset({5,9})}}
        token_to_ssid_set = {2: frozenset({5,9}), 3: frozenset({5,9}), 4: frozenset({5,16})}

        i_cluster = clusterSimilarSSIDSets.cluster(TOKENS_TO_PROBES, ssid_set_to_tokens, ssid_set_to_matches, 
            token_to_ssid_set, check_fingerprints=False)
        clusters = list(i_cluster)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0], {2,3,4})

    def test_cluster_ordered(self):
        ssid_tuple_to_tokens = {(1,2) : {1,2}, (3,4): {2,3}, (5,6): {2,3,4}, (7,8): {5}}
        token_to_ssid_tuples = {1: {(1,2)}, 2:{(1,2), (3,4), (5,6)}, 3: {(3,4), (5,6)}, 4: {(5,6)}, 5: {(7,8)}}
        
        i_cluster = clusterOrderedSSIDSets.cluster(ssid_tuple_to_tokens, token_to_ssid_tuples)
        clusters = list(i_cluster)
        self.assertEqual(len(clusters), 2)
        self.assertEqual(clusters[0], {1,2,3,4})
        self.assertEqual(clusters[1], {5})


class TestFilterWithFingerprint(unittest.TestCase):

    def test_filter_outlier_fingerprint(self):
        token_to_probes_fingerprints = {1: [{"timestamp": 531, "ssid": 5, "fingerprint": "F_ONE"}], 
                    2: [{"timestamp": 242, "ssid": 5, "fingerprint": "F_TWO"}, {"timestamp": 643, "ssid": 9, "fingerprint": "F_TWO"}], 
                    3: [{"timestamp": 999999995, "ssid": 5, "fingerprint": "F_TWO"}, {"timestamp": 999999999, "ssid": 9, "fingerprint": "F_TWO"}],
                    4: [{"timestamp": 264, "ssid": 5, "fingerprint": "F_THREE"}, {"timestamp": 895, "ssid": 16, "fingerprint": "F_THREE"}],
                    5: [{"timestamp": 5839, "ssid": 5, "fingerprint": "F_FOUR"}, {"timestamp": 6435, "ssid": 9, "fingerprint": "F_FOUR"}]}

        old_cluster = {2,3,5}
        # Whilst SSID sets of token 2,3 and 5 are the same. Token 5 has different fingerprint.
        new_cluster = clusterSimilarSSIDSets.filter_false_pos_tokens_from_cluster(
                        token_to_probes_fingerprints, old_cluster)

        # Token 5 has been filtered.
        self.assertEqual(new_cluster, {2,3})



if __name__ == '__main__':
    unittest.main()
