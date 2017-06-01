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
        // We can set this to true when user moved or zoomed map
        this.interacted = false;
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
        let detectInteract = (evt) => {
            // Check if user event or because of method like Map.flyTo
            if (evt.originalEvent) {
                this.interacted = true;
                this.emit('interacted');
                console.info("User has interacted with map");
            }
        }
        this.map.once('movestart', detectInteract);
        this.map.once('zoomstart', detectInteract);
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
            // Update athlete marker position
            let am = this.athleteMarkers[track.user_id];
            // TODO: Set last updated time
            if (am) {
                am.setLngLat(lastpt);
                this.fitToAthleteMarkers();
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
        let el = document.createElement('div');
        // Identify message type
        el.className = 'msg-marker ' + msg.className;
        // Show message text
        let txt = msg.text || '';
        // Shorten if too long
        if (txt.length > 22) {
            txt = txt.slice(0,22) + '...';
        }
        el.innerHTML = txt;

        el.addEventListener('click', (ev) => {
            this.emit('msgClick', msg.id);
        });

        if (msg.coordinates !== undefined) {
            new mapboxgl.Marker(el, {
                offset: [0, -20]
            }).setLngLat(msg.coordinates.slice(0, 2)).addTo(this.map);
        }
    }
    addAthleteMarker(athlete) {
        let el = document.createElement('div');
        el.className = 'athlete-marker';

        let nameBox = document.createElement('div');
        nameBox.className = 'namebox';
        nameBox.innerHTML = athlete.first_name;

        let picBox = document.createElement('div');
        picBox.className = 'picbox';
        picBox.innerHTML = '';

        let svgLine = document.createElement('svg');
        el.appendChild(svgLine);
        svgLine.outerHTML = `
        <svg width="48" height="64" viewBox="0 0 48 64"
            xmlns="http://www.w3.org/2000/svg">

        <line x1="24" y1="24" x2="24" y2="64"
                stroke-width="4" stroke="grey" stroke-linecap="round"/>
        </svg>`;

        // Add in reverse order of desired z-index
        el.appendChild(picBox);
        el.appendChild(nameBox);

        el.addEventListener('click', (ev) => {
            this.emit('athleteClick', athlete.id);
        });

        let marker = new mapboxgl.Marker(el, {
            offset: [0,0]
        }).setLngLat([0,0]).addTo(this.map);

        this.athleteMarkers[athlete.id] = marker;
    }
    fitToAthleteMarkers() {
        let bounds = new mapboxgl.LngLatBounds();
        let valid = false;
        // Iteration function gets first value then key
        forEach(this.athleteMarkers, (marker, ath_id) => {
            let lnglat = marker.getLngLat();
            // Only if marker has position other than initial 0,0
            if (lnglat.lng || lnglat.lat) {
                bounds.extend(lnglat);
                valid = true;
            }
        });

        // Only if user has not yet interacted with the map
        if (valid && !this.interacted) {
            this.map.fitBounds(bounds);
            // Zoom out a little for padding
            // This is kind of a hack, Turf.js handles it more nicely
            // this.map.setZoom(this.map.getZoom() - 1);
        }
    }
}

export {Map};
