There are many amazing adventurers that do incredible things, yet cannot communicate these effectively to their followers. Let's change that, let's take people along for a ride.

A related issue is that it is hard to attract big sponsors to sailplane and paragliding races because they're not very spectator-friendly. Let's change that too and bring gliding, hanggliding and paragliding to the Olympics!

Here's some random lyric for inspiration.

*Come along and you´ll see... what it's like to be free* Come Along - Titiyo

## Idea
These are some untested ideas. Someone should go out into the field and find out if this is what people want.

There are four types of data that an adventurer can generate:
- Text
- Images
- Audio
- Video

One can be accompanied by another. This data makes up the narrative of the story. We must present it such that the spectator can actually follow the story.

Next comes interaction; spectators should be able to interact with the adventurer in some (possibly rate-limited) way.

To present the data and enable interaction, we can use four widgets:
- Map; gps tracks and markers.
- Timeline; markers (video was recorded here) and ranges (walking/sleeping). Not crucial (can be hidden on small screens) but does give spectator a good temporal intuition of events.
- Blog; media from adventurers belonging to markers.
- Chat; messages of spectators and replies from adventurers.

These can be presented in different layouts depending on device.

## System architecture
I sat down, thought long and hard, then designed a modular architecture around standalone worker processes that communicate using (redis) pub/sub channels, with some tasks outsourced to [redis-queue](python-rq.org). To get the media into the system, [Telegram](telegram.org) is ideal as it supports all mobile platforms and has extensive APIs. It does require some fiddling when using it in-flight, but saves us from natively implementing things like video recording, transcoding, and uploading.

Here's the full diagram:

![System architecture](https://raw.githubusercontent.com/The-Fonz/come-along/master/system-diagram.png)

## Client implementation and requirements
Here's some requirements mixed with implementation details. *MSG_CLICK* is a pub/sub event.

- Map
  - Show athlete routes, markers
  - Should zoom to include all athlete's positions initially
  - Pan to 
  - 2D should be fast (use [Leaflet](leafletjs.com))
  - 3D version should be fast (Cesium is quite heavy, but implementing this is for later)
  - Restrict pan to adventure bounding box
  - Markers have icons indicating type of msg
  - Emit *MSG_CLICK* on marker click
  - Pan to msg on *MSG_CLICK* without zooming, and panning as little as possible (e.g. so that event is within 25% of center)

- Timeline
  - Should show all adventurer msgs
  - Should have option to group msgs per adventurer
    - If selected, should show adventurer state ranges (sleeping/walking)
  - Restrict zoom to start-end of adventure (+ margin)
  - Emit *MSG_CLICK* on marker click
  - Pan to msg on *MSG_CLICK*
  - Can be hidden on small screens

- Blog
  - Show all adventurer msgs
  - Scroll to msg on *MSG_CLICK*
  - Emit *MSG_CLICK* on interaction with msg (e.g. click video, audio element)
  - Shows # of new msgs in badge
  - Has like-button

- Chat
  - Show chat msgs of adventurer and spectators (can re-use blog widget with lighter styling)
  - Ask for name when sending msg
  - Shows # of new chat msgs in badge
  - Should have some kind of filtering or throttling

- About widget (who's doing this adventure anyway?)
  - Should show faces of all adventurers with about-me modal on click

- Extra features
  - In-browser persistence (e.g. localstorage) for fast loading and chat username remembering?
  - Spectator should be able to share on social media. Needs more thought.
  - Keep track of user, personalize page by showing new msgs?

- Layout
  - Show blog, map, chat as tabs on small screens, focus to right tab on *MSG_CLICK* 
  - Show map, timeline, blog vertically in medium/large portrait mode with expandable chat widget
  - Show map left, timeline and blog right on medium/large landscape mode screens with expandable chat widget
  
  
