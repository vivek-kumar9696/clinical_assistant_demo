import * as LiveKitClient from './livekit-client.js';

const { Room, RoomEvent, Track } = LiveKitClient;

const callBtn = document.getElementById('callBtn');
const status = document.getElementById('callStatus');
const wavePath = document.getElementById('wavePath');
const visualizerStage = document.getElementById('visualizerStage');

let room;
let isCalling = false;
let animationId;
let currentAmplitude = 0;
let phase = 0;

const LIVEKIT_URL = "wss://wardly-demo-vivek-rm3ctrsv.livekit.cloud";

// --- Bulletproof Button Listener ---
callBtn.addEventListener('click', async () => {
    callBtn.disabled = true; // Prevent double-clicks

    try {
        if (!isCalling) {
            await startLiveCall();
        } else {
            await stopLiveCall();
        }
    } finally {
        callBtn.disabled = false; // Re-enable when done
    }
});

async function startLiveCall() {
    if (room && (room.state === 'connected' || room.state === 'connecting')) {
        console.warn("Already connecting...");
        return;
    }

    isCalling = true;
    callBtn.innerText = "Connecting...";

    try {
        const tokenResponse = await fetch('http://localhost:8080/get-token');
        const { token } = await tokenResponse.json();

        room = new Room();

        room.on(RoomEvent.TrackSubscribed, (track) => {
            if (track.kind === Track.Kind.Audio) {
                console.log("Agent is speaking");
                const audioEl = track.attach();
                audioEl.autoplay = true;
                audioEl.style.display = "none";
                document.body.appendChild(audioEl);
            }
        });

        await room.connect(LIVEKIT_URL, token);
        await room.startAudio();
        await room.localParticipant.setMicrophoneEnabled(true);

        status.innerText = "Connected to room: " + room.name;
        callBtn.innerText = "End Call";

        // Activate the CSS ring
        visualizerStage.classList.add('active-call');

    } catch (error) {
        console.error("Connection error:", error);
        await stopLiveCall();
    }
}

// --- Bulletproof Disconnect Logic ---
async function stopLiveCall() {
    console.log("Disconnecting call...");
    callBtn.innerText = "Disconnecting...";
    isCalling = false; // Immediately drops the wave animation to idle state

    if (room) {
        // 1. Explicitly stop the microphone tracks to release hardware lock
        if (room.localParticipant) {
            const audioTracks = room.localParticipant.audioTrackPublications;
            audioTracks.forEach(publication => {
                if (publication.track) {
                    publication.track.stop();
                }
            });
        }

        // 2. Disconnect the room
        await room.disconnect();
        room = null;
    }

    // 3. Clean up lingering audio elements in the DOM
    const strayAudioElements = document.querySelectorAll('audio');
    strayAudioElements.forEach(audio => audio.remove());

    // 4. Reset UI
    callBtn.innerText = "Start Call";
    status.innerText = "System Ready";

    if (visualizerStage) {
        visualizerStage.classList.remove('active-call');
    }
}

// --- Dynamic Wave Animation Logic ---
function animateWave() {
    let maxVolume = 0;

    // Only check for volume if the call is actively connected
    if (isCalling && room) {
        // Strict fallback to 0 if the audio level is undefined at connection start
        room.remoteParticipants.forEach(p => {
            const vol = typeof p.audioLevel === 'number' ? p.audioLevel : 0;
            if (vol > maxVolume) maxVolume = vol;
        });

            if (room.localParticipant) {
                const localVol = typeof room.localParticipant.audioLevel === 'number' ? room.localParticipant.audioLevel : 0;
                if (localVol > maxVolume) maxVolume = localVol;
            }
    }

    // Target amplitude logic
    // Cap the max amplitude to 80 so the wave stays safely inside the 200px height
    const targetAmplitude = isCalling ? 5 + (maxVolume * 80) : 5;

    currentAmplitude += (targetAmplitude - currentAmplitude) * 0.2;
    phase += 0.15;

    let d = `M 0 100`;
    // Loop stops at 200 instead of 600
    for (let x = 0; x <= 200; x += 5) {
        // Envelope scales to 200 to keep the edges pinned to the left/right of the circle
        const envelope = Math.sin((x / 200) * Math.PI);

        // x * 0.05 increases the frequency so we get enough ripples in the smaller width
        const y = 100 + Math.sin((x * 0.05) + phase) * currentAmplitude * envelope;
        d += ` L ${x} ${y}`;
    }

    wavePath.setAttribute('d', d);
    animationId = requestAnimationFrame(animateWave);
}

// Start the idle "breathing" animation immediately on page load
animateWave();
