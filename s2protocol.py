#!/usr/bin/env python
#
# Copyright (c) 2013 Blizzard Entertainment
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import collections
import sys
import argparse
import pprint

from mpyq import mpyq
import protocol15405


class EventLogger:
    def __init__(self):
        self._event_stats = {}

    def log(self, output, event):
        # update stats
        if '_event' in event and '_bits' in event:
            stat = self._event_stats.get(event['_event'], [0, 0])
            stat[0] += 1  # count of events
            stat[1] += event['_bits']  # count of bits
            self._event_stats[event['_event']] = stat
        # write structure
        pprint.pprint(event, stream=output)

    def log_stats(self, output):
        for name, stat in sorted(self._event_stats.iteritems(), key=lambda x: x[1][1]):
            print >> output, '"%s", %d, %d,' % (name, stat[0], stat[1] / 8)


class Hots2Lambda:
    @staticmethod
    def flatten(dist, parent_key='', sep='_'):
        items = []
        for k, v in dist.items():
            new_key = parent_key + sep + str(k) if parent_key else k
            if isinstance(v, collections.MutableMapping):
                items.extend(Hots2Lambda.flatten(v, new_key, sep).items())
            elif isinstance(v, collections.Iterable):
                # log may contain list with a singleton item which is map,
                # for example, 500: [{'attrid': 500, 'namespace': 999, 'value': 'Humn'}]
                if len(v) == 1 and isinstance(v[0], collections.MutableMapping):
                    items.extend(Hots2Lambda.flatten(v[0], new_key, sep).items())
                else:
                    items.append((new_key, v))
            else:
                items.append((new_key, v))
        return dict(items)

    @staticmethod
    def dict2lambdalog(dist):
        log = ''
        for k, v in dist.items():
            kv = '{}[{}]'.format(k, v)
            log = log + ',' + kv if log else kv
        return log

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('replay_file', help='.SC2Replay file to load')
    parser.add_argument("--gameevents", help="print game events",
                        action="store_true")
    parser.add_argument("--messageevents", help="print message events",
                        action="store_true")
    parser.add_argument("--trackerevents", help="print tracker events",
                        action="store_true")
    parser.add_argument("--attributeevents", help="print attributes events",
                        action="store_true")
    parser.add_argument("--header", help="print protocol header",
                        action="store_true")
    parser.add_argument("--details", help="print protocol details",
                        action="store_true")
    parser.add_argument("--initdata", help="print protocol initdata",
                        action="store_true")
    parser.add_argument("--stats", help="print stats",
                        action="store_true")
    parser.add_argument("--all", help="dump all message in lambda-cloud log format",
                        action="store_true")
    args = parser.parse_args()

    archive = mpyq.MPQArchive(args.replay_file)

    logger = EventLogger()

    # Read the protocol header, this can be read with any protocol
    contents = archive.header['user_data_header']['content']
    header = protocol15405.decode_replay_header(contents)
    if args.header:
        logger.log(sys.stdout, header)

    # The header's baseBuild determines which protocol to use
    baseBuild = header['m_version']['m_baseBuild']
    try:
        protocol = __import__('protocol%s' % (baseBuild,))
    except:
        print >> sys.stderr, 'Unsupported base build: %d' % baseBuild
        protocol = __import__('protocol34835')
        # sys.exit(1)

    # Print protocol details
    if args.details or args.all:
        contents = archive.read_file('replay.details')
        details = protocol.decode_replay_details(contents)
        #logger.log(sys.stdout, details)
        flatten = Hots2Lambda.flatten(details)
        log = Hots2Lambda.dict2lambdalog(flatten)
        print log

    # Print protocol init data
    if args.initdata:
        contents = archive.read_file('replay.initData')
        initdata = protocol.decode_replay_initdata(contents)
        # ogger.log(sys.stdout, initdata['m_syncLobbyState']['m_gameDescription']['m_cacheHandles'])
        # logger.log(sys.stdout, initdata)
        flatten = Hots2Lambda.flatten(initdata)
        log = Hots2Lambda.dict2lambdalog(flatten)
        print log

    # Print game events and/or game events stats
    if args.gameevents or args.all:
        contents = archive.read_file('replay.game.events')
        for event in protocol.decode_replay_game_events(contents):
            # if event['_event'] == 'NNet.Game.SUnitClickEvent':
            # logger.log(sys.stdout, event)
            flatten = Hots2Lambda.flatten(event)
            log = Hots2Lambda.dict2lambdalog(flatten)
            print log

    # Print message events
    if args.messageevents or args.all:
        contents = archive.read_file('replay.message.events')
        for event in protocol.decode_replay_message_events(contents):
            #logger.log(sys.stdout, event)
            flatten = Hots2Lambda.flatten(event)
            log = Hots2Lambda.dict2lambdalog(flatten)
            print log

    # Print tracker events
    if args.trackerevents or args.all:
        if hasattr(protocol, 'decode_replay_tracker_events'):
            contents = archive.read_file('replay.tracker.events')
            for event in protocol.decode_replay_tracker_events(contents):
                # logger.log(sys.stdout, event)
                flatten = Hots2Lambda.flatten(event)
                log = Hots2Lambda.dict2lambdalog(flatten)
                print log

    # Print attributes events
    if args.attributeevents or args.all:
        contents = archive.read_file('replay.attributes.events')
        attributes = protocol.decode_replay_attributes_events(contents)
        # logger.log(sys.stdout, attributes)
        flatten = Hots2Lambda.flatten(attributes)
        log = Hots2Lambda.dict2lambdalog(flatten)
        print log

    # Print stats
    if args.stats:
        logger.log_stats(sys.stderr)
