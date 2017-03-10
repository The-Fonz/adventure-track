import EventEmitter from 'events';
import map from 'lodash/map';
import clone from 'lodash/clone';
import moment from 'moment';
import forEach from 'lodash/forEach';
import sortedIndexBy from 'lodash/sortedIndexBy';
import {Athlete_stream, Msg_stream, Track_stream} from './datastreams.js';


/**
 * Keeps track of all data, will contains some methods that operate
 * on all data.
 */
class Db extends EventEmitter {
    constructor() {
        super();
        // For initiating dummy streams
        this.athlete_stream = new Athlete_stream();
        this.msg_stream = new Msg_stream();
        this.track_stream = new Track_stream();
        // Tracks by athlete id
        // {'<athlete-id>': {'coordinates': [],
        // 'timestamps': []}, ...}
        this.tracks = [];
        // Athletes by id
        // {<athlete-id>: {id: 'ab123', name: 'Dude'}, ...}
        this.athletes = {};
        // *Inversely* chronologically ordered list of messages,
        // so newest first (easy rendering), sorted at all times
        // [{athlete_id: 'ab123', id: 'msgid1239214', text: 'Hi there!',
        //   timestamp: "2017-03-07T20:58:12"}, ...]
        this.messages = [];

        this.msg_stream.on('newMsgs', (newMsgs) => {
            let cleanedMsgs = [];
            // Insert at proper place, do not assume times are sequential
            forEach(newMsgs, (m) => {
                let cleanm = this._cleanMsg(m);
                cleanedMsgs.push(cleanm);
                // Use inverse unix timestamp (in seconds)
                let insertAt = sortedIndexBy(this.messages, cleanm,
                       elem => -elem.timestamp.unix());
                // Delete 0
                this.messages.splice(insertAt, 0, cleanm);
            });
            // Not guaranteed to be sorted correctly
            this.emit('newMsgs', cleanedMsgs);
        });

        this.track_stream.on('newTracks', (newTracks) => {
            forEach(newTracks, (t) => {
                // Initialize arrays if needed
                if (this.tracks[t.id] === undefined) {
                    this.tracks[t.id] = {coordinates: [],
                                         timestamps: []};
                }
                // Assume proper ordering, no duplicates
                forEach(t['timestamps'], (ts) => {
                    this.tracks[t.id]['timestamps'].push(ts);
                });
                forEach(t['coordinates'], (pt) => {
                    this.tracks[t.id]['coordinates'].push(pt);
                });
            });
            this.emit('newTracks', newTracks);
        });

        this.athlete_stream.on('newAthletes', (newAthletes) => {
            forEach(newAthletes, (a) => {
                this.athletes[a.id] = a;
            });
            // No event emitted, should use ractive to listen to this.athletes
        });
    }

    /**
     * Convert msg to have vis.Timeline compatible attributes.
     * Does not mutate msg.
     */
    _cleanMsg(msg) {
        let out = clone(msg);
        if (out['timestamp']) {
            out['timestamp'] = moment(out['timestamp']);
            out['start'] = out['timestamp'];
        }
        // Infer message types from attributes
        // Default is text, and image/audio/video overrides in that order
        let msgType = 'text';
        if (out['image_versions']) msgType = 'image';
        if (out['audio_versions']) msgType = 'audio';
        if (out['video_versions']) msgType = 'video';
        // For vis.Timeline icon styling
        out['className'] = 'msgtype-' + msgType;
        out.content = "";
        return out;
    }
}

export {Db};
