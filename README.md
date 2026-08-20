# pyBedrockConnect

A lightweight Python UDP relay for Minecraft Bedrock servers.

`pyBedrockConnect` appears as a LAN server, responds to Bedrock/RakNet discovery pings, automatically tests a list of remote Bedrock servers, selects the server with the lowest UDP response latency, and then relays traffic between the Bedrock client and the selected server.

The entire tool runs from a single file:

## Features
* You can easily modify the bedrock version and protocol version for developers and beta testers
  ```py
  # Change the values according to you game 
  PROTOCOL_VERSION = 12168  # Settings > General (At the bottom)
  VERSION = "1.26.44" # Mainmenu (bottom right)
  ```
* Automatically stops after 5 seconds without traffic from the remote server
* Designed to be easy to run on mobile phones and even microcontrollers 

## Requirements

Python 3 (No `pip install` is required.)




## Running
Copy the code below and run its that simple.

- Android **Coding Python** (Used it for testing no ads) - [Coding Python on Google Play](https://play.google.com/store/apps/details?id=com.kvassyu.coding.py)



```python
#!/usr/bin/python3

import socket
import struct
import select
import time

# Change the values according to you game 
PROTOCOL_VERSION = 12168  # Settings > General (At the bottom)
VERSION = "1.26.44" # Mainmenu (bottom right)
PORT = 19132
REMOTE_PORT = 19132

IPS = [
    "104.238.130.180",
    "134.255.231.119",
    "185.169.180.190",
    "5.161.83.73",
    "213.171.211.142",
    "217.160.58.93"
]

MAGIC = bytes.fromhex(
    "00 ff ff 00 fe fe fe fe fd fd fd fd 12 34 56 78"
)

SERVER_GUID = 0x7165B97802C172E1

SERVER_NAME = (
    f"MCPE;crafted by brostos;{PROTOCOL_VERSION};{VERSION};0;10;0;pyBedrockConnect;"
    "survival;1;19132;19132"
).encode()

def build_ping():
    timestamp = int(time.time() * 1000)
    return (
        b"\x01"
        + struct.pack(">Q", timestamp)
        + MAGIC
        + struct.pack(">Q", SERVER_GUID)
    )


def find_best_server():
    best_ip = None
    best_latency = float("inf")
    payload = build_ping()

    print("Finding fastest BedrockConnect server...")

    for ip in IPS:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.5)

        start = time.perf_counter()

        try:
            sock.sendto(payload, (ip, REMOTE_PORT))
            data, _ = sock.recvfrom(2048)

            latency = (time.perf_counter() - start) * 1000

            if data and data[0] == 0x1C:
                print(f"-> {ip:<15} {latency:7.2f} ms")

                if latency < best_latency:
                    best_latency = latency
                    best_ip = ip
            else:
                print(f"-> {ip:<15} Invalid response")

        except socket.timeout:
            print(f"-> {ip:<15} Timeout")

        except OSError:
            print(f"-> {ip:<15} Unreachable")

        finally:
            sock.close()

    if best_ip is None:
        print("No reachable Bedrock server found.")
        return None

    print(
        f"Selected {best_ip} "
        f"({best_latency:.2f} ms)"
    )

    return best_ip


def build_pong(timestamp):
    return (
        b"\x1c"
        + struct.pack(">Q", timestamp)
        + struct.pack(">Q", SERVER_GUID)
        + MAGIC
        + struct.pack(">H", len(SERVER_NAME))
        + SERVER_NAME
    )


def main():
    remote_ip = find_best_server()

    if remote_ip is None:
        return

    lan = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    lan.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lan.bind(("0.0.0.0", PORT))

    remote = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    remote.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    remote.bind(("0.0.0.0", 0))

    server = (remote_ip, REMOTE_PORT)

    client = None
    connected = False
    online = False
    online_activity = None

    print(f"Proxy started on {"0.0.0.0"}:{PORT}")
    print(f"Forwarding to {remote_ip}:{REMOTE_PORT}")

    try:
        while True:
            if online:
                remaining = 5 - (
                    time.monotonic() - online_activity
                )

                if remaining <= 0:
                    break
            else:
                remaining = None

            readable, _, _ = select.select(
                [lan, remote],
                [],
                [],
                remaining
            )

            if not readable:
                break

            for sock in readable:
                if sock is lan:
                    data, addr = lan.recvfrom(65535)

                    if not data:
                        continue

                    if data[0] == 0x01:
                        if len(data) < 33 or data[9:25] != MAGIC:
                            continue

                        timestamp = struct.unpack(
                            ">Q",
                            data[1:9]
                        )[0]

                        lan.sendto(
                            build_pong(timestamp),
                            addr
                        )
                        continue

                    client = addr
                    remote.sendto(data, server)

                    if not online:
                        online = True
                        online_activity = time.monotonic()

                elif sock is remote:
                    data, _ = remote.recvfrom(65535)
                    online_activity = time.monotonic()

                    if client is None:
                        continue

                    lan.sendto(data, client)

                    if not connected:
                        connected = True
                        print(
                            f"Player connected to BedrockConnect"
                            f"-> {remote_ip}:{REMOTE_PORT}"
                        )

    except (OSError, KeyboardInterrupt):
        pass

    finally:
        lan.close()
        remote.close()

        if connected:
            print("Player successfully transported through proxy")
        else:
            print("Proxy stopped.")


if __name__ == "__main__":
    main()
```


## Changing the Remote Servers

Edit the `IPS` list:

```python
IPS = [
    "104.238.130.180",
    "134.255.231.119",
    "185.169.180.190",
    "5.161.83.73"
]
```

The proxy will test every address and select the fastest one that returns a valid RakNet Offline Pong.

## Acknowledgments

- **BedrockConnect**: Special thanks to [Pugmatt](https://github.com/Pugmatt/BedrockConnect) server provider.
- **PieRakNet**: Special thanks to [PieMC-Dev](https://github.com/PieMC-Dev/PieRakNet) used during testing and learing the protocol.

## License

This project is licensed under the [MIT License](LICENSE). See the `LICENSE` file for details.
