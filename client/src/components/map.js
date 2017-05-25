import EventEmitter from 'events';
import forEach from 'lodash/forEach';
import mapboxgl from 'mapbox-gl';

mapboxgl.accessToken = process.env.MAPBOX_ACCESSTOKEN;

let geojsonLine = function (coords) {
    return {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "LineString",
            "coordinates": coords
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

        // Milliseconds
        let waittimeout = 5;

        let addsrc = () => {
            try {
                this.map.addSource(srcname, src);
            } catch (e) {
                waittimeout *= 2;
                console.info(`Failed to add source to map, trying again after ${waittimeout}ms, reason: ${e}`);
                // Schedule self again...
                window.setTimeout(addsrc, waittimeout);
                // Avoid continuing with rest of func
                return;
            }
            // Do this only if successfully adding source
            this.map.addLayer({
                "id": layername,
                "type": "line",
                "layout": {"line-join": "round", "line-cap": "round"},
                "paint": {"line-color": "#F00", "line-width": 4},
                "source": srcname,
            });
        }

        window.setTimeout(addsrc, waittimeout);
    }
    updateTracks(newTracks) {
        for (let track of newTracks) {
            // Create internal track if new
            if (this.geojsons[track.user_id] === undefined) {
                this.geojsons[track.user_id] = geojsonLine([]);
            }
            // Now update internal track with new points
            let lastpt = [0,0];
            forEach(track.coordinates, (pt)=>{
                lastpt = pt.slice(0,2);
                this.geojsons[track.user_id].geometry.coordinates.push(lastpt);
            });
            // Go to last position
            // TODO: Don't do this, if multiple tracks it jumps around
            this._flyTo(lastpt);
            // Update athlete marker position
            let am = this.athleteMarkers[track.user_id];
            if (am) {
                am.setLngLat(lastpt);
            }

            // Now update external (map) track
            let srcname = `source-athleteid-${track.user_id}`;
            let src = this.map.getSource(srcname);
            // Create if not exists
            if (src === undefined) {
                // this.map.setCenter(track.coordinates[0].slice(0,2));
                // Geojson needs to be wrapped like this in order to
                // adhere to mapboxGL source definition spec, see:
                // https://www.mapbox.com/mapbox-gl-style-spec/#sources
                this.addTrack(track.user_id, {
                    "type": "geojson",
                    "data": this.geojsons[track.user_id]
                });
            } else {
                src.setData(this.geojsons[track.user_id]);
            }
        }
    }
    _flyTo(lonlat) {
        this.map.easeTo({center: lonlat});
    }
    addMsgMarker(msg) {
        console.log(msg);
        let el = document.createElement('div');
        // Identify message type
        el.className = 'msg-marker ' + msg.className;
        // Show message text
        el.innerHTML = msg.text || '';

        el.addEventListener('click', (ev) => {
            this.emit('msgClick', msg.id);
        });

        if (msg.coordinates !== undefined) {
            new mapboxgl.Marker(el, {
                offset: [0, 0]
            }).setLngLat(msg.coordinates.slice(0, 2)).addTo(this.map);
        }
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
