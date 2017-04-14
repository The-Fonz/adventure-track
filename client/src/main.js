import autobahn from 'autobahn';
import Ractive from 'ractive';
import forEach from 'lodash/forEach';
import vis from 'vis';
import {Db} from './components/db.js';
import {Map} from './components/map.js';

import fade from 'ractive-transitions-fade';

function widthMax(w) {
    return window.matchMedia(`(max-device-width: ${w}px)`).matches;
}

/*
 * Wire up db, map and timeline
 */

let db = new Db();

let map = new Map('map-view');

db.on('newTracks', (newTracks) => {
    map.updateTracks(newTracks);
});

let items = new vis.DataSet(db.messages);
let options = {width: '100%', height: '150px',
    orientation: {axis: 'top', item: 'top'}};
let timeline = new vis.Timeline(
    document.getElementById('timeline'), items, options);

db.on('newMsgs', (newMsgs) => {
    forEach(newMsgs, (m) => {
        items.add(m);
        map.addMsgMarker(m);
    });
    timeline.fit();
});

db.on('newAthletes', (newAthletes) => {
    forEach(newAthletes, (a) => {
        map.addAthleteMarker(a);
    });
});

/*
 * AUTOBAHN
 */

var wsuri = `ws://${window.location.host}/ws`;

// the WAMP connection to the Router
var connection = new autobahn.Connection({
    url: wsuri,
    realm: "realm1"
});

document.connection = connection;

// fired when connection is established and session attached
connection.onopen = function (session, details) {

    console.log("Connected");

    let uid = window.location.pathname.split('/')[2];

    function receiveMsgHandler(msgs) {
        db.msg_stream.receiveMsgs(msgs);
    }

    session.call('at.public.messages.fetchmsgs', [uid]).then(
        // Receives response
        receiveMsgHandler,
        // Error handler
        // TODO: Send to sentry (automatic?)
        (err) => {
            console.error("Error fetching messages");
            let errmsg = "There was an error loading the messages. We've been notified!";
            blog.set('messagesLoadError', errmsg);
        }
    );

    // Unpack list of args
    session.subscribe(`at.messages.user.${uid}`, args => receiveMsgHandler(args[0])).then(
        sub => console.log('subscribed to topic'),
        err => console.error('failed to subscribe')
    );
};

// fired when connection was lost (or could not be established)
connection.onclose = function (reason, details) {
    console.log("Connection lost: " + reason);
};

// now actually open the connection
connection.open();

/*
 * RACTIVE
 */
function sendAnalyticsEvent(evt) {
    // Assume session has been instantiated
    connection.session.call('at.public.analytics.insert_event', [evt])
        // TODO: Send to Sentry
        .catch(err => console.error("Failed to send analytics event"));
}

let blog = new Ractive({
    el: document.getElementById('blog'),
    template: document.getElementById('blog-template').innerHTML,
    transitions: {
        fade: fade,
    },
    data: {
        // Make sure that messages have an id to keep same dom elements
        messages: db.messages,
        // Keys are message id's
        likes: {},
        // Can be set externally
        messagesLoadError: null
    },
    modifyArrays: true,
    highlight: function (id) {
        console.log("Highlight msg "+ id);
    },
    like: function (msg_id) {
        // Set keypath corresponding to likes[msg_id]
        this.set('likes.'+msg_id, true);
        let evt = {'type': 'msglike', 'extra': {'msg_id': msg_id}};
        sendAnalyticsEvent(evt);
    }
});

let overlay = new Ractive({
    el: document.getElementById('overlay'),
    template: document.getElementById('overlay-template').innerHTML,
    transitions: {
        fade: fade,
    },
    data: {
        visible: false,
        vidsrc: null,
        imgsrc: null
    },
    oninit: function() {
        // Event.get() is msg obj
        blog.on('show', (event) => {
            let msg = event.get();
            sendAnalyticsEvent({'type': 'msgclick', 'extra': {'msg_id': msg.id}});
            // Clear vid/img
            this.set('vidsrc', null);
            this.set('imgsrc', null);
            let res = '1080';
            // Do basic content resolution selection based on device width
            if (widthMax(1400)) {
                res = '720';
            } else if (widthMax(800)) {
                res = '360';
            }
            if (msg.video_versions) {
                this.set('vidsrc', '/media/'+msg.video_versions[res]);
            } else if (msg.image_versions) {
                this.set('imgsrc', '/media/'+msg.image_versions[res]);
            }
            this.set('visible', true);
            return false;
        });
    },
    close: function() {
        // Stop video play

        this.set('visible', false);
    }
});

// Export for use in main-test
export {db, map, blog, overlay, timeline};
