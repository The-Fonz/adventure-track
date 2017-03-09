import Rx from 'rxjs';
import moment from 'moment';

// Interval of 3s after 4s
let timesource3s = Rx.Observable.interval(3000);

let example_athletes = [
    {'id': '123', 'name': 'Johnny'}
];

let example_messages = [
    {'id': 1, 'msgtype': 'text', 'text': 'hithere', 'timestamp': '2017'},
    {'id': 2, 'msgtype': 'text', 'text': 'msg2', 'timestamp': '2017-03-06'},
    {'id': 3, 'msgtype': 'text', 'text': 'msg3', 'timestamp': '2017-03-07'},
    {'id': 4, 'msgtype': 'text', 'text': 'msg4', 'timestamp': '2017-03-07'},
];

let athlete_stream = Rx.Observable.interval(1000);

let track_stream = Rx.Observable.interval(2000).map((a) => {
    return {'123': {'coordinates': [[a, Math.random()*3], [a, Math.random()*4]],
                    'timestamps': ['2017-03-08', '2017-04-12']}};
}).take(180);

let msg_stream = timesource3s
    .map((i) => {
        let msg = example_messages[i];
        // Convert to vis.Timeline compatible attributes
        if (msg['timestamp']) {
            msg['timestamp'] = moment(msg['timestamp']);
            msg['start'] = msg['timestamp'];
        }
        if (msg['msgtype']) {
            msg['className'] = 'msgtype-'+msg['msgtype'];
        }
        msg.content = "";
        return msg;
    }).take(example_messages.length);

export {athlete_stream, msg_stream, track_stream};
