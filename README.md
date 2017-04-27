# directed-probe-matching
Apply MAC address randomisation to a dataset, and then attempt to deanonymise devices by matching similar preferred network lists.

The following scripts have been developed to demonstrate how directed probes can be used to fingerprint and track devices despite MAC address randomisation.

Requirements to run:

- Python 3.6
- PyShark
- A .pcap file containing (directed) probe requests.

Usage:

Note: Steps 1 and 2 are pre-requisites to subsequent steps.

1) Parse .pcap into a JSON file containing probe requests mapped to MAC addresses:

Run parsePackets.py ensuring capture_file_path points to the correct file.
E.g. 

```
$ python3.6 parsePackets.py
[====================] 100% (3040000)
Processed 3049698 packets with 0 errors and 9606 filtered packets.
[]
```

Optional: To include fingerprint of information elements (e.g. hardware capabilities) use flag --fingerprint

2) Randomise MAC addresses within output JSON file:

Run randomiseToTokens.py
E.g.

```
$ python3.6 randomiseToTokens.py
Applying MAC randomisation to probes.
Tokens total: 58568
Calculating valid pairs of tokens...
MACs sending directed probes: 9994
Tokens sending directed probes: 29484
Total pairs:  434638386
Valid pairs: 84698
Invalid pairs: 434553688
```

Optional: To include fingerprint of information elements (e.g. hardware capabilities) use flag –fingerprint

Note: Default lifetime for a token is 12 hours, set randomisation_interval to a different timedelta to change this.

3) Cluster randomised MAC addresses (“tokens”) that probe for the same SSID set.

Run clusterSameSSIDSet.py
E.g.

```
$ python3.6 clusterSameSSIDSet.py 
Matching tokens with the same SSID set.
Validating clusters...
{'accuracy': 0.9998199514757079,
 'clusters': 5569,
 'fn': 74251,
 'fp': 4005,
 'fpr': 9.216352571836877e-06,
 'macs': 1006,
 'median': datetime.timedelta(13, 86390, 694971),
 'tn': 434549683,
 'tp': 10447,
 'tpr': 0.12334411674419703}
```

Note: SSID sets with cardinality less than two are ignored due to high rate of false positives.

The script outputs a binary classification. Including number of MACs tracked for period exceeding 12 hours, and their median duration tracked. 

4) Cluster randomised MAC addresses (“tokens) that probe for n-tuples of SSID.

Run clusterOrderedSSIDSets.py
E.g. 

```
$ python3.6 clusterOrderedSSIDSets.py 
Matching tokens sharing 6-tuples of SSIDs.
Clustering tokens with shared 6-tuples of SSIDs.
{'accuracy': 0.9998288117147572,
 'clusters': 3454,
 'fn': 71117,
 'fp': 3288,
 'fpr': 7.566383834257092e-06,
 'macs': 945,
 'median': datetime.timedelta(14, 26937, 754457),
 'tn': 434550400,
 'tp': 13581,
 'tpr': 0.1603461711020331}
```

Note: Default value for n is 6.

5) Cluster randomised MAC addresses (“tokens”) that probe for similar SSID sets.

Run clusterSimilarSSIDSets.py
E.g.

```
$ python3.6 clusterSimilarSSIDSets.py 
Matching tokens with the same SSID set.
Matching SSID sets with a Jaccard similarity index greater than 0.67
Clustering tokens with similar SSID sets.
{'accuracy': 0.999838422002607,
 'clusters': 4220,
 'fn': 66070,
 'fp': 4158,
 'fpr': 9.568437950985702e-06,
 'macs': 1262,
 'median': datetime.timedelta(15, 282, 807498),
 'tn': 434549530,
 'tp': 18628,
 'tpr': 0.2199343550024794}
```

6) Cluster randomised MAC addresses (“tokens”) that probe for similar SSID sets, with cross-check that removes tokens with differing fingerprints (i.e. different hardware capabilities). This has been found to reduce the rate of false positives.

Run clusterSimilarSSIDSets.py –-fingerprint
E.g. 

```
$ python3.6 clusterSimilarSSIDSets.py --fingerprint
Matching tokens with the same SSID set.
Matching SSID sets with a Jaccard similarity index greater than 0.67
Clustering tokens with similar SSID sets.
Filtering false positive matchings from cluster by comparing device fingerprints.
{'accuracy': 0.9998455050289317,
 'clusters': 4220,
 'fn': 66619,
 'fp': 535,
 'fpr': 1.2310647004576822e-06,
 'macs': 1213,
 'median': datetime.timedelta(15, 3364, 431720),
 'tn': 434582635,
 'tp': 18081,
 'tpr': 0.2134710743801653}
```

7) Test step(6) with token lifetimes varying from 1 second to original 12 hours. Used to test the effectiveness of matching with respect to more aggressive randomisation.

Run runForRandomisationPeriods.py
