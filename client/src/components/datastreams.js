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


class User_stream extends EventEmitter {
    constructor() {
        super();
    }
    receiveUsers(users) {
        if (isArray(users)) {
            this.emit('newUsers', users);
        } else {
            this.emit('newUsers', [users]);
        }
    }
}

export {User_stream, Msg_stream, Track_stream};
