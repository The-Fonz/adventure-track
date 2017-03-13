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

// Export for use in main-test
export {db, map, blog, overlay, timeline};
