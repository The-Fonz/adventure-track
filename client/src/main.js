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

let db = new Db();

let map = new Map('map-view');

let blog = new Ractive({
    el: document.getElementById('blog'),
    template: document.getElementById('blog-template').innerHTML,
    transitions: {
        fade: fade,
    },
    data: {
        // Make sure that messages have an id to keep same dom elements
        messages: db.messages,
    },
    modifyArrays: true,
    highlight: function (id) {
        console.log("Highlight msg "+ id);
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
                this.set('vidsrc', msg.video_versions[res]);
            } else if (msg.image_versions) {
                this.set('imgsrc', msg.image_versions[res]);
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

var wsuri = "ws://127.0.0.1:8080/ws";

// the WAMP connection to the Router
var connection = new autobahn.Connection({
    url: wsuri,
    realm: "realm1"
});

document.connection = connection;

// fired when connection is established and session attached
connection.onopen = function (session, details) {

    console.log("Connected");

    let uid = Number(window.location.pathname.split('/')[2]);

    session.call('com.messages.fetchmsgs', [uid]).then((res)=>{
            db.msg_stream.receiveMsgs(res);
        });

    // SUBSCRIBE to a topic and receive events
    //
    function on_counter (args) {
        var counter = args[0];
        console.log("on_counter() event received with counter " + counter);
    }
    session.subscribe('com.example.oncounter', on_counter).then(
        function (sub) {
            console.log('subscribed to topic');
        },
        function (err) {
            console.log('failed to subscribe to topic', err);
        }
    );

    // PUBLISH an event
    // session.publish('com.example.onhello', ['Hello from JavaScript (browser)']);

    // REGISTER a procedure for remote calling
    function mul2 (args) {
        var x = args[0];
        var y = args[1];
        console.log("mul2() called with " + x + " and " + y);
        return x * y;
    }
    session.register('com.example.mul2', mul2).then(
        function (reg) {
            console.log('procedure registered');
        },
        function (err) {
            console.log('failed to register procedure', err);
        }
    );

    // CALL a remote procedure
    // session.call('com.example.add2', [x, 18]).then(
    //         function (res) {
    //             console.log("add2() result:", res);
    //         },
    //         function (err) {
    //             console.log("add2() error:", err);
    //         }
    //     );
};

// fired when connection was lost (or could not be established)
//
connection.onclose = function (reason, details) {
    console.log("Connection lost: " + reason);
}

// now actually open the connection
//
connection.open();

// Export for use in main-test
export {db, map, blog, overlay, timeline};
