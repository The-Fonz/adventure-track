/*
 * Compiling this module includes some tape tests
 */

import {db} from './main.js';
import test from 'tape';
import range from 'lodash/range';
import forEach from 'lodash/forEach';

// Have to run a http server in repo root for devdata!
let msgDumRun = fetch('/testdata/stjean/msgs.json')
    .then(resp => resp.json())
    .then((dummyMsgs) => {
        // Assuming dummyMsgs to be in chronological order
        function sendDummyMsg() {
            // How many to send at once
            let n = Math.ceil(Math.random()*2);
            let out = [];
            // Take oldest dummyMsgs
            forEach(
                range(Math.min(n, dummyMsgs.length)),
                i => out.push(dummyMsgs.shift()));
            db.msg_stream.receiveMsgs(out);
            // Only schedule if still example msgs left
            if (dummyMsgs.length) {
                // Wait between (0,10) seconds
                window.setTimeout(() => sendDummyMsg(), Math.random() * 10000);
            }
        }
        sendDummyMsg();
    });

// let trackDumRun = fetch('/testdata/stjean/stjean.json')
//     .then(resp => resp.json())
//     .then((dummyTracks) => {
//         main.db.track_stream.startDummy(dummyTracks);
//     });

// function sum(a,b) {
//     return a+b;
// }
//
// test('sum should return addition', function (t) {
//     t.equal(3, sum(1,2));
//     t.end();
// });

// Run tests only when dummy data is flowing
// Promise.all([msgDumRun], ...
