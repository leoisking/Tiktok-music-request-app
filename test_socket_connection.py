"""Read-only connection smoke test for an already-running widget server."""

import argparse
import threading

import socketio


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:5000', help='Widget server origin')
    args = parser.parse_args()
    client = socketio.Client(reconnection=False)
    state_received = threading.Event()

    @client.on('update_queue')
    def on_queue(data):
        if isinstance(data, list):
            state_received.set()

    try:
        client.connect(args.url, transports=['polling'], wait_timeout=10)
        response = client.call('request_state', {}, timeout=5)
        if not isinstance(response, dict) or not response.get('success') or not state_received.wait(5):
            print('[FAILED] Connected, but no queue snapshot was received.')
            return 1
        print('[OK] Connected and received current state. No queue or playback changes were made.')
        return 0
    except Exception as error:
        print(f'[FAILED] {error}')
        return 1
    finally:
        if client.connected:
            client.disconnect()


if __name__ == '__main__':
    raise SystemExit(main())
