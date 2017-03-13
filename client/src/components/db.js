import EventEmitter from 'events';
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
        this.tracks = {};
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
                cleanm = this._joinMsgAthlete(cleanm);
                cleanm = this._addMsgLocation(cleanm);
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
                let aid = t.athlete_id;
                // Initialize arrays if needed
                if (this.tracks[aid] === undefined) {
                    this.tracks[aid] = {coordinates: [],
                                         timestamps: []};
                }
                // Assume proper ordering, no duplicates
                forEach(t['timestamps'], (ts) => {
                    // Convert to moment object
                    this.tracks[aid]['timestamps'].push(moment(ts));
                });
                forEach(t['coordinates'], (pt) => {
                    this.tracks[aid]['coordinates'].push(pt);
                });
            });
            this.emit('newTracks', newTracks);
        });

        this.athlete_stream.on('newAthletes', (newAthletes) => {
            forEach(newAthletes, (a) => {
                this.athletes[a.id] = a;
            });
            this.emit('newAthletes', newAthletes);
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

    /**
     * Join athlete with msg
     */
    _joinMsgAthlete(msg) {
        let a = this.athletes[msg.athlete_id];
        if (a) {
            msg.athlete = a;
        }
        return msg;
    }

    /**
     * Add location to message
     */
    _addMsgLocation(msg) {
        // TODO: Handle case where athlete doesn't exist, and where
        //       there is no track or no track points yet
        // Try last track point if msg does not have its own location
        if (msg.coordinates === undefined) {
            let athletetrack = this.tracks[msg.athlete_id];
            // Take last track point before msg timestamp
            let insertAt = sortedIndexBy(athletetrack['timestamps'],
                                        msg.timestamp);
            msg.coordinates = athletetrack['coordinates'][insertAt-1].slice(0,2);
        }
        return msg;
    }
}

export {Db};
