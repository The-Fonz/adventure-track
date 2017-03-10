import EventEmitter from 'events';
import isArray from 'lodash/isArray';


class Track_stream extends EventEmitter {
    constructor() {
        super();
    }
    receiveTracks(tracks) {
        this.emit('newTracks', tracks);
    }
}


class Msg_stream extends EventEmitter {
    constructor() {
        super();
    }
    receiveMsgs(msgs) {
        // Emits array of received messages
        if (isArray(msgs)) {
            this.emit('newMsgs', msgs);
        } else {
            this.emit('newMsgs', [msgs]);
        }
    }
}


class Athlete_stream extends EventEmitter {
    constructor() {
        super();
    }
    receiveAthletes(athletes) {
        if (isArray(athletes)) {
            this.emit('newAthletes', athletes);
        } else {
            this.emit('newAthletes', [athletes]);
        }
    }
}

export {Athlete_stream, Msg_stream, Track_stream};
