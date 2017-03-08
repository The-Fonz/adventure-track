<style lang="stylus">
#mapboxglmap
    height 100%
</style>

<template lang="jade">
div
    div#mapboxglmap
</template>

<script>
import {tracks} from './db';
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

let pts = [[0,0]];

export default {
    subscriptions: {
        // Tracks by athlete id
        // {'<athlete-id>': {'coordinates': [],
        // 'timestamps': []}, ...}
        tracks$: tracks,
    },
    data: function () {
        return {
            map: null,
        }
    },
    mounted: function () {
        this.map = new mapboxgl.Map({
            container: 'mapboxglmap',
            style: 'mapbox://styles/mapbox/outdoors-v9'
        });
        this.map.on('load', () => {
            this.addTrack();
            // Start observing here
            this.$observables.tracks$.subscribe((msg) => {
                console.log(msg);
                pts.push(msg);
                if (this.map) {
                    this.map.getSource('athleteid-track-source').setData(
                        coordsToLine(pts)
                    );
                } else {
                    console.log("Map not yet created")
                }
            });
        });
    },
    methods: {
        /** Adds track */
        addTrack: function () {
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
        },
    },
}
</script>