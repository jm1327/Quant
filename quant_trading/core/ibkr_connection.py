#!/usr/bin/env python3
"""Base Interactive Brokers TWS connection utilities."""

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
import threading
import time


class IBKRConnection(EWrapper, EClient):
    """Base class for IBKR TWS connections."""

    def __init__(self, client_id: int = 1):
        EClient.__init__(self, self)
        self.client_id = client_id
        self.connected = False
        self.next_order_id = None

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        """Handle errors returned by the TWS API."""
        print(f"Error {errorCode}: {errorString}")

    def nextValidId(self, orderId):
        """Receive the next valid order ID, signalling a live connection."""
        print(f"Connection successful! Next valid order ID: {orderId}")
        self.next_order_id = orderId
        self.connected = True
        self.on_connection_established()

    def on_connection_established(self):
        """Hook for subclasses once a connection has been established."""

    def connect_to_tws(self, host: str = "127.0.0.1", port: int = 7497, timeout: int = 10) -> bool:
        """Connect to IBKR TWS or Gateway."""
        try:
            print(f"Connecting to TWS at {host}:{port} with client ID {self.client_id}...")
            self.connect(host, port, self.client_id)

            api_thread = threading.Thread(target=self.run, daemon=True)
            api_thread.start()

            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.5)

            if not self.connected:
                print(f"Connection timeout after {timeout} seconds")
                return False

            return True

        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"Connection failed: {exc}")
            return False

    def disconnect_from_tws(self):
        """Disconnect from TWS."""
        if self.connected:
            self.disconnect()
            self.connected = False
            print("Disconnected from TWS")

    def wait_for_completion(self, check_condition, timeout: int = 30, check_interval: int = 1) -> bool:
        """Poll a condition until it returns True or times out."""
        start_time = time.time()
        while not check_condition() and (time.time() - start_time) < timeout:
            time.sleep(check_interval)

        if time.time() - start_time >= timeout:
            print(f"Operation timeout after {timeout} seconds")
            return False

        return True

    def is_connected(self) -> bool:
        """Return True if the TWS connection is live."""
        return self.connected
