<style lang="stylus">
.half
    width: 50%
    height: 100%
.left
    float: left
.right
    float: right
/* Avoid text select on double click */
.noselect
    -webkit-user-select: none; /* webkit (safari, chrome) browsers */
    -moz-user-select: none; /* mozilla browsers */
    -khtml-user-select: none; /* webkit (konqueror) browsers */
    -ms-user-select: none; /* IE10+ */
</style>

<template lang="jade">
div
    div.half.left.noselect
        map-view
    div.half.right
        timeline
        blog
</template>

<script>
//import {tracks} from './db';

import Timeline from './timeline.vue';
import Blog from './blog.vue';
import MapView from './map.vue';

export default {
    subscriptions: {
        // Tracks by athlete id
        // {'<athlete-id>': {'coordinates': [],
        // 'timestamps': []}, ...}
//        tracks$: tracks,
    },
    components: {
        MapView,
        Blog,
        Timeline
    },
    data () {
        return {
            // List of athletes with attributes
            // [{id: 123, name: 'Dude'}, ...]
            athletes: [],
            // Chronologically ordered list of messages
            // [{athlete_id: 123, text: 'Hi there!',
            // timestamp: "2017-03-07T20:58:12"}, ...]
            messages: [],
        }
    },
    mounted: function () {
//        this.$observables.tracks$.subscribe(msg => console.log(msg));
    },
    methods: {}
}
</script>