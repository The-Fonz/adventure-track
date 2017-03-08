import Rx from 'rxjs/Rx';
import axios from 'axios';

let example_athletes = {
    '123': {'name': 'Johnny'}
};

let example_messages = [
    {'type': 'text', 'text': 'hithere', 'timestamp': '2017'}
];

let athletes = Rx.Observable.interval(1000).map((a) => {

}).take(4);

let tracks = Rx.Observable.interval(2000).map(a => [a, Math.random()*3]).take(180);

let messages = Rx.Observable.interval(6000).map((i) => {

});

if (process.env.TEST === 'true') {
    console.log("Compiled with TEST=true, making mock db");
    // DbObservable = MockDb;
} else {
    // DbObservable = RealDb;
}

export {tracks};
