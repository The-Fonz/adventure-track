import EventEmitter from 'events';
import {athlete_stream, msg_stream, track_stream} from './dummystreams.js';

if (process.env.TEST === 'true') {
    console.log("Compiled with TEST=true, making mock db");
    // DbObservable = MockDb;
} else {
    // DbObservable = RealDb;
}




// db.messages.subscribe((newMsg) => {
//     // Append to beginning
//     messages.unshift(newMsg);
// });
// // Can be used for new or updating
// db.athletes.subscribe((newAthlete) => {
//     athletes[newAthlete.id] = newAthlete;
// });

class Db extends EventEmitter {
    constructor() {
        super();
        // Tracks by athlete id
        // {'<athlete-id>': {'coordinates': [],
        // 'timestamps': []}, ...}
        this.tracks = [];
        // Athletes by id
        // {<id>: {id: 123, name: 'Dude'}, ...}
        this.athletes = {};
        // Chronologically ordered list of messages
        // [{athlete_id: 123, text: 'Hi there!',
        //   timestamp: "2017-03-07T20:58:12"}, ...]
        this.messages = [];

        msg_stream.subscribe((newMsg) => {
            // Append to beginning
            this.messages.unshift(newMsg);
            this.emit('newMsg', newMsg);
        });

        track_stream.subscribe((newTracks) => {
            for (let key in newTracks) {
                if (this.tracks[key]) {
                    this.tracks[key]['coordinates'] = this.tracks[key]['coordinates'].concat(newTracks[key]['coordinates']);
                    this.tracks[key]['timestamps'] = this.tracks[key]['timestamps'].concat(newTracks[key]['timestamps']);
                } else {
                    this.tracks[key] = newTracks[key];
                }
            }
            this.emit('newTrack', newTracks);
        });
    }
}

export {Db};
