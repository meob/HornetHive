const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const mqtt = require('mqtt');
const fs = require('fs');
const path = require('path');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

// --- CONFIGURATION ---
const ASSET_HEARTBEAT_TIMEOUT = 30000; // 30 seconds
const WATCHDOG_INTERVAL = 5000;       // Check every 5 seconds

// Load Scenarios
let SCENARIOS = {};
try {
    const data = fs.readFileSync(path.join(__dirname, 'assets', 'scenarios.json'), 'utf8');
    SCENARIOS = JSON.parse(data);
} catch (e) {
    console.error("[!] Failed to load scenarios.json:", e.message);
    process.exit(1);
}

// Parse Command Line Args
const args = process.argv.slice(2);

if (args.includes('--help')) {
    console.log(`
\x1b[36mHORNET HIVE | C4I STATION - CLI HELP\x1b[0m

Usage: node server.js [OPTIONS]

Options:
  --scenario [NAME]   Select mission scenario (e.g., FUKUSHIMA_PLANT, BONIFACIO_STRAIT). Default: HORNET_HOME
  --log               Enable logging of key mission events to logs/mission_events_YYYY-MM-DD.log
  --debug             Enable verbose tracing to logs/debug_trace_YYYY-MM-DD.log
  --verbose           Enable verbose console output (shows all telemetry)
  --help              Show this help message
`);
    process.exit(0);
}

const scenarioArgIndex = args.indexOf('--scenario');
const SELECTED_SCENARIO_KEY = (scenarioArgIndex !== -1 && args[scenarioArgIndex + 1]) 
    ? args[scenarioArgIndex + 1].toUpperCase() 
    : 'HORNET_HOME';

const ENABLE_LOG = args.includes('--log');
const ENABLE_DEBUG = args.includes('--debug');
const VERBOSE_MODE = args.includes('--verbose');

if (!SCENARIOS[SELECTED_SCENARIO_KEY]) {
    console.error(`[!] Invalid Scenario: ${SELECTED_SCENARIO_KEY}. Available: ${Object.keys(SCENARIOS).join(', ')}`);
    process.exit(1);
}

const ACTIVE_SCENARIO = SCENARIOS[SELECTED_SCENARIO_KEY];
console.log(`\x1b[36m[*] MISSION PROFILE: ${SELECTED_SCENARIO_KEY} (${ACTIVE_SCENARIO.description})\x1b[0m`);
if (ENABLE_LOG) console.log(`\x1b[33m[*] LOGGING ENABLED (Mission Events)\x1b[0m`);
if (ENABLE_DEBUG) console.log(`\x1b[31m[*] DEBUG MODE ENABLED (Full Trace)\x1b[0m`);
if (VERBOSE_MODE) console.log(`\x1b[35m[*] VERBOSE CONSOLE ENABLED\x1b[0m`);

app.use(express.static('public'));

// Setup Logging
const LOG_DIR = path.join(__dirname, 'logs');
if (!fs.existsSync(LOG_DIR)) fs.mkdirSync(LOG_DIR);

const getDateStr = () => new Date().toISOString().split('T')[0];
let missionLogStream = null;
let debugLogStream = null;

if (ENABLE_LOG) {
    missionLogStream = fs.createWriteStream(path.join(LOG_DIR, `mission_events_${getDateStr()}.log`), {flags: 'a'});
}
if (ENABLE_DEBUG) {
    debugLogStream = fs.createWriteStream(path.join(LOG_DIR, `debug_trace_${getDateStr()}.log`), {flags: 'a'});
}

const MQTT_HOST = process.env.MQTT_HOST || 'localhost';
const mqttClient = mqtt.connect(`mqtt://${MQTT_HOST}:1883`);
let activeAssets = {}; 
let aiWatchdogTimer = null;

mqttClient.on('connect', () => {
    console.log("\x1b[32m[*] GCS BACKEND: Connected to MQTT Broker\x1b[0m");
    mqttClient.subscribe(['hive/drone/+/telemetry', 'hive/alerts/#', 'hive/operator/confirm', 'hive/ai/feedback', 'hive/swarm/target', 'hive/target/+/telemetry', 'hive/weather/+/telemetry']);
    
    // Publish Scenario Config (Retained) for Drones
    mqttClient.publish('hive/sys/config', JSON.stringify({
        home_lat: ACTIVE_SCENARIO.lat,
        home_lon: ACTIVE_SCENARIO.lon,
        scenario: SELECTED_SCENARIO_KEY,
        mission_type: ACTIVE_SCENARIO.mission_type,
        spatial_markers: ACTIVE_SCENARIO.spatial_markers || {}
    }), { retain: true });
});

mqttClient.on('message', (topic, message) => {
    let data;
    try {
        const payload = message.toString();
        if (!payload) return; 
        data = JSON.parse(payload);
    } catch (e) {
        return; 
    }
    const timestamp = new Date().toISOString();
    let isTacticalEvent = false;
    let isTelemetry = false;
    
    // Logging Formattato
    let logColor = "\x1b[37m"; // White
    if (topic.includes('drone') && topic.includes('telemetry')) {
        logColor = "\x1b[32m"; // Green
        isTelemetry = true;
        activeAssets[data.id] = { ...data, lastSeen: Date.now(), type: 'DRONE' };
        io.emit('asset_update', data);
    } 
    else if (topic.includes('target') && topic.includes('telemetry')) {
        logColor = "\x1b[36m"; // Cyan
        isTelemetry = true;
        activeAssets[data.id] = { ...data, lastSeen: Date.now(), type: 'TARGET' };
        io.emit('target_update', data);
    }
    else if (topic.includes('alerts/status')) {
        logColor = "\x1b[34m"; // Blue
        isTacticalEvent = false;
        activeAssets[data.sensor] = { 
            ...data,
            id: data.sensor, 
            lastSeen: Date.now(), 
            type: 'SENSOR' 
        };
        io.emit('tactical_status', data);
    }
    else if (topic.includes('alerts/detection')) {
        logColor = "\x1b[31m"; // Red
        isTacticalEvent = true;
        if (activeAssets[data.sensor]) activeAssets[data.sensor].lastSeen = Date.now();
        io.emit('tactical_alert', data);
    }
    else if (topic.includes('alerts/mission_success')) {
        logColor = "\x1b[32m"; // Green
        isTacticalEvent = true;
        io.emit('mission_success', data);
    }
    else if (topic.includes('alerts/mayday')) {
        logColor = "\x1b[31m"; // Red (Bold/Blink in UI)
        isTacticalEvent = true;
        io.emit('tactical_mayday', data);
    }
    else if (topic.includes('operator/confirm')) {
        logColor = "\x1b[35m"; // Magenta
        isTacticalEvent = true;
        if (activeAssets[data.sensor]) activeAssets[data.sensor].lastSeen = Date.now();
        io.emit('operator_confirmation', data);
    }
    else if (topic.includes('ai/feedback')) {
        logColor = "\x1b[35m"; // Magenta
        isTacticalEvent = true;
        // Clear AI watchdog on any feedback
        if (aiWatchdogTimer) {
            clearTimeout(aiWatchdogTimer);
            aiWatchdogTimer = null;
        }
        io.emit('ai_feedback', data);
    }
    else if (topic.includes('swarm/target')) {
        logColor = "\x1b[33m"; // Yellow
        isTacticalEvent = true;
    }
    else if (topic.includes('weather/')) {
        logColor = "\x1b[34m"; // Blue
        isTacticalEvent = false;
        const weatherId = data.id || 'SENS_UNKNOWN';
        activeAssets[`W_${weatherId}`] = { ...data, lastSeen: Date.now(), type: 'WEATHER' };
        io.emit('weather_update', data);
    }

    const logEntry = `[${timestamp}] ${topic} -> ${JSON.stringify(data)}`;
    
    // 1. Mission Event Logging (Selective & Sanitized)
    if (ENABLE_LOG && isTacticalEvent && missionLogStream) {
        let logData = { ...data };
        if (logData.snapshot && logData.snapshot.length > 50) {
            logData.snapshot = "[BASE64_IMAGE_TRUNCATED]";
        }
        const cleanEntry = `[${timestamp}] ${topic} -> ${JSON.stringify(logData)}`;
        missionLogStream.write(cleanEntry + '\n');
    }

    // 2. Debug Trace Logging (Full)
    if (ENABLE_DEBUG && debugLogStream) {
        debugLogStream.write(logEntry + '\n');
    }
    
    // Console Output Logic
    // Suppress high-frequency data (telemetry/weather) unless tactical or verbose mode is on
    if (isTacticalEvent || VERBOSE_MODE) {
        let displayData = { ...data };
        if (displayData.snapshot && displayData.snapshot.length > 50) {
            displayData.snapshot = displayData.snapshot.substring(0, 50) + "... (truncated)";
        }
        const displayLog = `[${timestamp}] ${topic} -> ${JSON.stringify(displayData)}`;
        console.log(`${logColor}${displayLog}\x1b[0m`);
    }
});

// --- WATCHDOG TIMER ---
setInterval(() => {
    const now = Date.now();
    Object.keys(activeAssets).forEach(id => {
        const asset = activeAssets[id];
        // Only timeout if it was previously ONLINE or other active states
        if (asset.status !== 'OFFLINE' && asset.status !== 'DISCONNECTED' && (now - asset.lastSeen) > ASSET_HEARTBEAT_TIMEOUT) {
            console.log(`\x1b[33m[!] WATCHDOG: Asset ${id} timed out. Marking OFFLINE.\x1b[0m`);
            asset.status = (asset.type === 'SENSOR') ? 'OFFLINE' : 'DISCONNECTED';
            
            if (asset.type === 'SENSOR') {
                io.emit('tactical_status', { sensor: id, status: 'OFFLINE' });
            } else {
                io.emit('asset_update', asset);
            }
        }
    });
}, WATCHDOG_INTERVAL);

// Bridge Comandi Browser -> MQTT
io.on('connection', (socket) => {
    // 1. Send Scenario Config
    socket.emit('init_scenario', {
        lat: ACTIVE_SCENARIO.lat,
        lon: ACTIVE_SCENARIO.lon,
        zoom: ACTIVE_SCENARIO.zoom,
        name: SELECTED_SCENARIO_KEY
    });

    // 2. Send full state of assets
    Object.values(activeAssets).forEach(asset => {
        if (asset.type === 'DRONE') socket.emit('asset_update', asset);
        if (asset.type === 'TARGET') socket.emit('target_update', asset);
        if (asset.type === 'MAYDAY') socket.emit('tactical_mayday', asset);
        if (asset.type === 'WEATHER') socket.emit('weather_update', asset);
        if (asset.type === 'SENSOR') socket.emit('tactical_status', { 
            ...asset,
            sensor: asset.id
        });
    });

    socket.on('dispatch_mission', (payload) => {
        mqttClient.publish('hive/swarm/target', JSON.stringify(payload));
    });

    socket.on('ai_objective', (payload) => {
        mqttClient.publish('hive/ai/objective', JSON.stringify(payload));
        
        // AI Watchdog: Check if commander responds within 10s
        if (aiWatchdogTimer) clearTimeout(aiWatchdogTimer);
        aiWatchdogTimer = setTimeout(() => {
            io.emit('ai_feedback', {
                status: "OFFLINE",
                log: "AI Commander is not responding. Check if assets/commander_ai.py is running."
            });
            aiWatchdogTimer = null;
        }, 10000); 
    });
});

app.get('/health', (req, res) => {
  res.status(200).send('OK');
});

server.listen(3000, () => console.log('[*] GCS UI: http://localhost:3000'));
