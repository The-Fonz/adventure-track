/*
 * Compiling this module includes some tape tests
 */

import {db, map, blog, overlay, timeline} from './main.js';
import test from 'tape';
import clone from 'lodash/clone';
import forEach from 'lodash/forEach';
import moment from 'moment';

// Global fake time, set when receiving testdata
let fakeTime = moment("2000");
// Holds moment date wrappers
let msgTimes = [];
// Milliseconds
let TIME_BETWEEN_MSGS = 2000;
// Pause this long at every message, in ms
let PAUSE_AT_MSG = 3000;

let msgIndex = 0;
function runTimeSim() {
    let spd = (msgTimes[msgIndex+1] - msgTimes[msgIndex]) / TIME_BETWEEN_MSGS;
    fakeTime.add(spd*10);
    if (fakeTime >= msgTimes[msgIndex+1]) {
        msgIndex += 1;
        // Pause if at msg
        window.setTimeout(runTimeSim, PAUSE_AT_MSG);
        console.info("Time between msgs was "+spd);
    } else {
        // Run every 10ms
        window.setTimeout(runTimeSim, 10);
    }
}

let athDumRun = fetch('/testdata/stjean/athletes.json')
    .then(resp => resp.json())
    .then((dummyAthletes) => {
        db.athlete_stream.receiveAthletes(dummyAthletes);
    });

// Have to run a http server in repo root for devdata!
let msgDumRun = fetch('/testdata/stjean/msgs.json')
    .then(resp => resp.json())
    .then((dummyMsgs) => {
        fakeTime = moment(dummyMsgs[1].timestamp);
        forEach(dummyMsgs, msg => msgTimes.push(moment(msg.timestamp)));
        runTimeSim();
        // Assuming dummyMsgs to be in chronological order
        function sendDummyMsg() {
            // Only if still example msgs left
            if (dummyMsgs.length) {
                let out = [];
                while (moment(dummyMsgs[0].timestamp) <= fakeTime) {
                    out.push(dummyMsgs.shift());
                    if (dummyMsgs.length === 0) break;
                }
                db.msg_stream.receiveMsgs(out);
                window.setTimeout(() => sendDummyMsg(), 200);
            }
        }
        sendDummyMsg();
    });

let trackDumRun = fetch('/testdata/stjean/track.json')
    .then(resp => resp.json())
    .then((dummyTracks) => {
        let index = 0;
        function sendDummyTrack() {
            let out = [];
            for (let track of dummyTracks) {
                let t = clone(track);
                t['coordinates'] = [];
                t['timestamps'] = [];
                // Take all points after current time
                while (moment(track['timestamps'][index]) <= fakeTime) {
                    if (index > track['timestamps'].length) break;
                    // console.log('while dummytracks '+track['timestamps'][0] +' <= '+fakeTime.toISOString());
                    // From lon/lat to lat/lon
                    let coords = track['coordinates'][index];
                    t['coordinates'].push([coords[1],coords[0],coords[2]]);
                    t['timestamps'].push(track['timestamps'][index]);
                    index++;
                }
                // Only if non-empty
                if (t['coordinates'].length) {
                    out.push(t);
                }
            }
            db.track_stream.receiveTracks(out);
            window.setTimeout(() => sendDummyTrack(), 100);
        }
        sendDummyTrack();
    });

// Debugging introspection
document.db = db;
document.map = map;
document.blog = blog;
document.overlay = overlay;
document.timeline = timeline;

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
