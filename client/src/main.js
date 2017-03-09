import {Db} from './components/db.js';
import {Map} from './components/map.js';
import vis from 'vis';
import Ractive from 'ractive';

let db = new Db();

let map = new Map('map-view');

let ractive = new Ractive({
    el: document.getElementById('blog'),
    template: document.getElementById('blog-template').innerHTML,
    data: {
        messages: db.messages,
    },
    modifyArrays: true,
    select: function (id) {
        console.log("Clicked msg "+ id)
    },
});

db.on('newTrack', (newMsg) => {
    map.updateTrack();
});

let items = new vis.DataSet(db.messages);
let options = {width: '100%', height: '150px',
orientation: {axis: 'top', item: 'top'}};
let timeline = new vis.Timeline(
    document.getElementById('timeline'), items, options);

db.on('newMsg', (newMsg) => {
    items.add(newMsg);
});
