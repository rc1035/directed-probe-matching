#!/usr/bin/env python3.6

"""
Cluster together probes belonging to tokens that share similar SSID sets,
for token lifetimes varying from 1 second to 12 hours. 
Used to test the effectiveness of matching with respect to more aggressive randomisation.
"""

__author__ = "Richard Cosgrove"
__license__ = "MIT"

import randomiseToTokens
import clusterSameSSIDSet
import clusterSimilarSSIDSets

from datetime import datetime, timedelta
from pprint import pprint

times = [
timedelta(seconds=1),
timedelta(seconds=30),
timedelta(minutes=1),
timedelta(minutes=15),
timedelta(minutes=30),
timedelta(minutes=45),
timedelta(hours=1),
timedelta(hours=3),
timedelta(hours=6),
timedelta(hours=12)
]


for t in times:
	print("Randomisation period:", t)
	randomiseToTokens.main(include_fingerprints=True, randomisation_interval=t)
	clusterSimilarSSIDSets.main(check_fingerprints=True)
