#!/usr/bin/env python3
"""
Test script to verify Socket.IO communication between control server and widget server.
Run this while both servers are running to test the connection.
"""

import socketio
import time
import traceback

def main():
    print("\n" + "="*60)
    print("  Socket.IO Connection Test")
    print("="*60 + "\n")

    # Test 1: Connect to widget server as a client (like control_server.py does)
    print("[TEST 1] Connecting to widget server as Socket.IO client...")
    print("Target: http://localhost:5000")
    print()

    # Try with minimal logging first
    client = None
    try:
        print("Creating Socket.IO client...")
        client = socketio.Client(logger=False, engineio_logger=False, reconnection=False)

        connected = False
        connect_error = None

        @client.on('connect')
        def on_connect():
            nonlocal connected
            connected = True
            print("[OK] Connected to widget server!")

        @client.on('disconnect')
        def on_disconnect():
            nonlocal connected
            connected = False
            print("[DISCONNECT] Disconnected from widget server")

        @client.on('connect_error')
        def on_connect_error(data):
            nonlocal connect_error
            connect_error = data
            print(f"[ERROR] Connection error: {data}")

        # Attempt connection with longer timeout
        print("Attempting to connect...")
        try:
            client.connect('http://localhost:5000', transports=['polling'], wait=True, wait_timeout=10)
            print(f"Connection state after connect: {client.connected}")
        except Exception as conn_err:
            print(f"[ERROR] Connection exception: {conn_err}")
            if connect_error:
                print(f"[ERROR] Additional error info: {connect_error}")
            raise

        time.sleep(2)

        if client.connected:
            print("[SUCCESS] Connection established and stable!")
            print()

            # Test 2: Try to emit mod_clear event
            print("[TEST 2] Sending 'mod_clear' event to widget server...")
            try:
                client.emit('mod_clear', {})
                time.sleep(1)
                print("[OK] Event sent - check widget terminal for response")
            except Exception as e:
                print(f"[ERROR] Failed to send mod_clear: {e}")
            print()

            # Test 3: Try to emit mod_reset event
            print("[TEST 3] Sending 'mod_reset' event to widget server...")
            try:
                client.emit('mod_reset', {})
                time.sleep(1)
                print("[OK] Event sent - check widget terminal for response")
            except Exception as e:
                print(f"[ERROR] Failed to send mod_reset: {e}")
            print()

            print("="*60)
            print("RESULTS:")
            print("- If you see 'Queue cleared' / 'Votes reset' in widget logs,")
            print("  then Socket.IO communication works!")
            print("- If nothing happened, check widget server logs.")
            print("="*60)

        else:
            print("[FAILED] Could not establish stable connection")
            print("The connection was made but immediately dropped.")
            print()
            print("POSSIBLE CAUSES:")
            print("1. Widget server is not running on port 5000")
            print("2. Socket.IO version mismatch")
            print("3. Namespace issue")
            print("4. CORS restrictions")

        # Cleanup
        print("\nCleaning up...")
        time.sleep(1)
        if client and client.connected:
            client.disconnect()

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        print("\nFull error details:")
        traceback.print_exc()

        if client and client.connected:
            try:
                client.disconnect()
            except:
                pass

    print("\n[DONE] Test complete\n")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        traceback.print_exc()
    finally:
        input("\nPress Enter to close...")
