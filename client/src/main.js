import Vue from 'vue';
import Rx from 'rxjs/Rx';
import VueRx from 'vue-rx';

import MainApp from './components/app.vue';

Vue.use(VueRx, Rx);

let vapp = new Vue({
    el: '#mainapp',
    render: h => h(MainApp),
});

export {vapp};
