from flask import Flask, render_template, request, jsonify
from pychannels import Channels
import os
import requests

app = Flask(__name__)

# Configuration for multiple Channels App clients
# Format: "Name1:IP1,Name2:IP2,..."
CHANNELS_APP_CLIENTS_STR = os.environ.get('CHANNELS_APP_CLIENTS')
CHANNELS_APP_PORT = 57000 # Standard Channels App API port

# Parse the client string into a list of dictionaries
CHANNELS_CLIENTS = []
if CHANNELS_APP_CLIENTS_STR:
    try:
        for client_pair in CHANNELS_APP_CLIENTS_STR.split(','):
            name, ip = client_pair.strip().split(':')
            CHANNELS_CLIENTS.append({"name": name.strip(), "ip": ip.strip()})
    except Exception as e:
        print(f"ERROR: Could not parse CHANNELS_APP_CLIENTS environment variable: {e}")
        CHANNELS_CLIENTS = [] # Clear if parsing fails

if not CHANNELS_CLIENTS:
    print("WARNING: CHANNELS_APP_CLIENTS environment variable not set or incorrectly formatted.")
    print("Please set CHANNELS_APP_CLIENTS to 'Name1:IP1,Name2:IP2,...'.")


@app.route('/')
def index():
    # Pass the list of clients to the template
    return render_template('index.html', clients=CHANNELS_CLIENTS)

@app.route('/control', methods=['POST'])
def control_channels():
    data = request.json
    target_device_ip = data.get('device_ip')
    action = data.get('action')
    value = data.get('value')
    # NEW: Get seek_amount from the request
    seek_amount = data.get('seek_amount')

    if not target_device_ip:
        return jsonify({"status": "error", "message": "No target device IP provided."}), 400

    if not any(client['ip'] == target_device_ip for client in CHANNELS_CLIENTS):
         return jsonify({"status": "error", "message": f"Device IP {target_device_ip} is not configured."}), 400

    client = Channels(target_device_ip, CHANNELS_APP_PORT)

    try:
        if action == 'toggle_pause':
            client.toggle_pause()
        elif action == 'channel_up':
            client.channel_up()
        elif action == 'channel_down':
            client.channel_down()
        elif action == 'previous_channel':
            client.previous_channel()
        elif action == 'play_channel':
            if value:
                client.play_channel(str(value))
            else:
                return jsonify({"status": "error", "message": "Channel number required for 'play_channel'."}), 400
        # MODIFIED: Handle seek with a specific amount
        elif action == 'seek':
            if seek_amount is not None:
                try:
                    seek_seconds = int(seek_amount)
                    client.seek(seek_seconds) # pychannels supports client.seek(seconds)
                except ValueError:
                    return jsonify({"status": "error", "message": "Seek amount must be an integer."}), 400
            else:
                return jsonify({"status": "error", "message": "Seek amount required for 'seek' action."}), 400
        elif action == 'toggle_mute':
            client.toggle_mute()
        elif action == 'stop':
            client.stop()
        # NEW: Added toggle_cc action
        elif action == 'toggle_cc':
            client.toggle_cc()
        elif action == 'navigate':
            if value:
                client.navigate(value)
            else:
                return jsonify({"status": "error", "message": "Section name required for 'navigate'."}), 400
        else:
            return jsonify({"status": "error", "message": "Invalid action"}), 400

        return jsonify({"status": "success", "message": f"Action '{action}' executed on {target_device_ip}."})

    except Exception as e:
        return jsonify({"status": "error", "message": f"Error controlling Channels App ({target_device_ip}): {e}"}), 500

@app.route('/channels_list', methods=['GET'])
def get_channels_list():
    target_device_ip = request.args.get('device_ip')

    if not target_device_ip:
        return jsonify({"status": "error", "message": "No target device IP provided for channel list."}), 400

    if not any(client['ip'] == target_device_ip for client in CHANNELS_CLIENTS):
         return jsonify({"status": "error", "message": f"Device IP {target_device_ip} is not configured."}), 400

    try:
        favorite_channels_url = f"http://{target_device_ip}:{CHANNELS_APP_PORT}/api/favorite_channels"
        response = requests.get(favorite_channels_url)
        response.raise_for_status()
        favorite_channels_data = response.json()

        channels_for_gui = []
        for channel in favorite_channels_data:
            if 'number' in channel and 'name' in channel:
                channels_for_gui.append({
                    "channel_number": channel['number'],
                    "name": channel['name']
                })

        channels_for_gui.sort(key=lambda x: float(x['channel_number']))

        return jsonify(channels_for_gui)
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "error", "message": f"Error fetching favorite channels from {target_device_ip}: {e}. Is the app running on this device?"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"An unexpected error occurred during channel list fetch: {e}"}), 500


@app.route('/status', methods=['GET'])
def get_status():
    target_device_ip = request.args.get('device_ip')

    if not target_device_ip:
        return jsonify({"status": "error", "message": "No target device IP provided for status."}), 400

    if not any(client['ip'] == target_device_ip for client in CHANNELS_CLIENTS):
         return jsonify({"status": "error", "message": f"Device IP {target_device_ip} is not configured."}), 400

    try:
        client = Channels(target_device_ip, CHANNELS_APP_PORT)
        status = client.status()
        return jsonify(status)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error fetching status from {target_device_ip}: {e}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)