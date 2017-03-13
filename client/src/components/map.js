import EventEmitter from 'events';
import forEach from 'lodash/forEach';
import mapboxgl from 'mapbox-gl';

mapboxgl.accessToken = process.env.MAPBOX_ACCESSTOKEN;

let geojsonLine = function (coords) {
    return {
        "type": "geojson",
        "data": {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            }
        }
    }
};

class Map extends EventEmitter {
    constructor(divid) {
        super();
        // Geojson cache per source name, {'<sourcename>': <geojson>}
        this.geojsons = {};
        this.athleteMarkers = {};
        this.map = new mapboxgl.Map({
            container: divid,
            style: 'mapbox://styles/mapbox/outdoors-v9',
            zoom: 12,
        });
        this.map.on('load', () => {
            // Do init stuff if needed
        });
    }
    addTrack(athleteid, src) {
        let srcname = `source-athleteid-${athleteid}`;
        let layername = `layer-athleteid-${athleteid}`;
        this.map.addSource(srcname, src);
        this.map.addLayer({
            "id": layername,
            "type": "line",
            "layout": {"line-join": "round", "line-cap": "round"},
            "paint": {"line-color": "#F00", "line-width": 6},
            "source": srcname,
        });
    }
    updateTracks(newTracks) {
        for (let track of newTracks) {
            let srcname = `source-athleteid-${track.athlete_id}`;
            let src = this.map.getSource(srcname);
            let lastpt = [0,0];
            // Update if exists
            if (src) {
                forEach(track.coordinates, (pt)=>{
                    lastpt = pt.slice(0,2);
                    this.geojsons[track.athlete_id].geometry.coordinates.push(lastpt);
                });
                this._flyTo(lastpt);
                // Update athlete marker position
                let am = this.athleteMarkers[track.athlete_id];
                if (am) {
                    am.setLngLat(lastpt);
                }
                src.setData(this.geojsons[track.athlete_id]);
            } else {
                this.map.setCenter(track.coordinates[0].slice(0,2));
                // Create if not exists
                this.geojsons[track.athlete_id] = geojsonLine([]).data;
                this.addTrack(track.athlete_id, geojsonLine([[0,0],[1,1]]));
            }
        }
    }
    _flyTo(lonlat) {
        this.map.easeTo({center: lonlat});
    }
    addMsgMarker(msg) {
        let el = document.createElement('div');
        // Identify message type
        el.className = 'msg-marker ' + msg.className;
        // Show message text
        el.innerHTML = msg.text || '';

        el.addEventListener('click', (ev) => {
            this.emit('msgClick', msg.id);
        });

        new mapboxgl.Marker(el, {
            offset: [0,0]
        }).setLngLat(msg.coordinates.slice(0,2)).addTo(this.map);
    }
    addAthleteMarker(athlete) {
        let el = document.createElement('div');
        el.className = 'athlete-marker';
        el.innerHTML = athlete.name;

        el.addEventListener('click', (ev) => {
            this.emit('athleteClick', athlete.id);
        });

        let marker = new mapboxgl.Marker(el, {
            offset: [0,0]
        }).setLngLat([0,0]).addTo(this.map);

        this.athleteMarkers[athlete.id] = marker;
    }
}

export {Map};
