import mapboxgl from 'mapbox-gl';

mapboxgl.accessToken = process.env.MAPBOX_ACCESSTOKEN;

let coordsToLine = function (coords) {
    return {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "LineString",
            "coordinates": coords
        }
    }
};

class Map {
    constructor(divid) {
        this.map = new mapboxgl.Map({
            container: divid,
            style: 'mapbox://styles/mapbox/outdoors-v9'
        });
        this.map.on('load', () => {
            this.init();
        });
    }
    init() {
        this.addTrack([[0,0],[10,10]]);
    }
    addTrack(pts) {
        this.map.addSource('athleteid-track-source', {
            "type": "geojson",
            "data": coordsToLine(pts)
        });
        this.map.addLayer({
            "id": "athleteid-track-layer",
            "type": "line",
            "layout": {"line-join": "round", "line-cap": "round"},
            "paint": {"line-color": "#0F0", "line-width": 6},
            "source": 'athleteid-track-source',
        });
    }
    updateTrack() {
        if (this.map) {
            let src = this.map.getSource('athleteid-track-source');
            if (src) {
                src.setData(coordsToLine([[0, 0], [10, -10]]));
            } else {
                console.warn("Map not yet created")
            }
        }
    }
}

export {Map};
