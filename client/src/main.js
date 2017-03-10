import {Db} from './components/db.js';
import {Map} from './components/map.js';
import Ractive from 'ractive';
import forEach from 'lodash/forEach';
import vis from 'vis';

let db = new Db();

let map = new Map('map-view');

let ractive = new Ractive({
    el: document.getElementById('blog'),
    template: document.getElementById('blog-template').innerHTML,
    data: {
        // Make sure that messages have an id to keep same dom elements
        messages: db.messages,
    },
    modifyArrays: true,
    select: function (id) {
        console.log("Clicked msg "+ id)
    },
});

db.on('newTracks', () => {
    // TODO: couple to actual tracks
    map.updateTrack();
});

let items = new vis.DataSet(db.messages);
let options = {width: '100%', height: '150px',
orientation: {axis: 'top', item: 'top'}};
let timeline = new vis.Timeline(
    document.getElementById('timeline'), items, options);

db.on('newMsgs', (newMsgs) => {
    forEach(newMsgs, m => items.add(m));
});

// Export for use in main-test
export {db};
