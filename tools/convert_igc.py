#!/usr/bin/env python

# Code comes from xcsoar module, specifically:
# `xcsoar.submodule/python/test/test_xcsoar.py`

# Needs xcsoar dependency, see pypi, which is not python3 compatible
import xcsoar
import argparse
import csv

# Parse command line parameters
parser = argparse.ArgumentParser(
    description='IGC file name...')

parser.add_argument('file_name', type=str)
parser.add_argument('--csv', action='store_true',
                    help="Export as csv")

args = parser.parse_args()

print "Init xcsoar.Flight, don't store flight in memory"
flight = xcsoar.Flight(args.file_name, False)

times = flight.times()

for dtime in times:
  takeoff = dtime['takeoff']
  release = dtime['release']
  landing = dtime['landing']

  print "Takeoff: {}, location {}".format(takeoff['time'], takeoff['location'])
  print "Release: {}, location {}".format(release['time'], release['location'])
  print "Landing: {}, location {}".format(landing['time'], landing['location'])

  print "Flight path from takeoff to release:"
  fixes = flight.path(takeoff['time'], release['time'])
  print "%s fixes" % len(fixes)

if args.csv:
    # Convert to csv
    fn = args.file_name.rsplit('.',1)[0]+'.csv'
    print "Exporting in csv format to file %s" % fn
    with open(fn, 'w') as f:
        writer = csv.writer(f, delimiter=',')
        for p in flight.path():
            writer.writerow([
                p[0].isoformat(),
                p[2]['latitude'],
                p[2]['longitude'],
                # Altitude in m?
                p[3]
            ])
