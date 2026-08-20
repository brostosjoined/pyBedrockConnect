import network
import socket
import struct
import select
import time

SSID = ""
PASSWORD = ""

PROTOCOL_VERSION = 12168
VERSION = "1.26.44"

PORT = 19132
REMOTE_PORT = 19132
ONLINE_TIMEOUT = 5000

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
    f"MCPE;crafted by brostos;{PROTOCOL_VERSION};{VERSION};0;10;0;"
    "pyBedrockConnect;survival;1;19132;19132"
).encode("utf-8")


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(SSID, PASSWORD)

        for _ in range(200):
            if wlan.isconnected():
                break
            time.sleep_ms(100)

    if wlan.isconnected():
        print("Connected to WiFi:", wlan.ifconfig())
    else:
        raise RuntimeError("WiFi connection failed")


def build_ping():
    timestamp = time.ticks_ms()

    return (
        b"\x01"
        + struct.pack(">Q", timestamp)
        + MAGIC
        + struct.pack(">Q", SERVER_GUID)
    )


def find_best_server():
    best_ip = None
    best_latency = 999999
    payload = build_ping()

    print("Finding fastest BedrockConnect server...")

    for ip in IPS:
        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        sock.settimeout(1.5)

        start = time.ticks_ms()

        try:
            sock.sendto(
                payload,
                (ip, REMOTE_PORT)
            )

            data, _ = sock.recvfrom(2048)

            latency = time.ticks_diff(
                time.ticks_ms(),
                start
            )

            if data and data[0] == 0x1C:
                print(
                    "-> {} | {} ms".format(
                        ip,
                        latency
                    )
                )

                if latency < best_latency:
                    best_latency = latency
                    best_ip = ip
            else:
                print(
                    "-> {} | Invalid response".format(
                        ip
                    )
                )

        except OSError:
            print(
                "-> {} | Unreachable".format(
                    ip
                )
            )

        finally:
            sock.close()

    if best_ip is None:
        print("No reachable Bedrock server found.")
        return None

    print(
        "Selected {} ({} ms)".format(
            best_ip,
            best_latency
        )
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
    connect_wifi()

    remote_ip = find_best_server()

    if remote_ip is None:
        return

    lan = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    lan.bind(
        ("0.0.0.0", PORT)
    )

    remote = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    remote.bind(
        ("0.0.0.0", 0)
    )

    server = (
        remote_ip,
        REMOTE_PORT
    )

    client = None
    connected = False
    online = False
    online_activity = 0

    print(
        "Proxy started on 0.0.0.0:{}".format(
            PORT
        )
    )

    print(
        "Forwarding to {}:{}".format(
            remote_ip,
            REMOTE_PORT
        )
    )

    try:
        while True:

            if online:
                elapsed = time.ticks_diff(
                    time.ticks_ms(),
                    online_activity
                )

                if elapsed >= ONLINE_TIMEOUT:
                    break

                timeout = (
                    ONLINE_TIMEOUT - elapsed
                ) / 1000
            else:
                timeout = None

            readable, _, _ = select.select(
                [lan, remote],
                [],
                [],
                timeout
            )

            if not readable:
                break

            for sock in readable:

                if sock is lan:

                    data, addr = lan.recvfrom(
                        2048
                    )

                    if not data:
                        continue

                    packet_id = data[0]

                    if packet_id == 0x01:

                        if (
                            len(data) < 33
                            or data[9:25] != MAGIC
                        ):
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

                    remote.sendto(
                        data,
                        server
                    )

                    online_activity = (
                        time.ticks_ms()
                    )

                    if not online:
                        online = True

                elif sock is remote:

                    data, _ = remote.recvfrom(
                        2048
                    )

                    online_activity = (
                        time.ticks_ms()
                    )

                    if client is None:
                        continue

                    lan.sendto(
                        data,
                        client
                    )

                    if not connected:
                        connected = True

                        print(
                            "Player connected -> "
                            "{}:{}".format(
                                remote_ip,
                                REMOTE_PORT
                            )
                        )

    except (OSError, KeyboardInterrupt):
        pass

    finally:
        lan.close()
        remote.close()

        if connected:
            print(
                "Player successfully transported "
                "through proxy"
            )
        else:
            print("Proxy stopped.")


connect_wifi()
remote_ip = find_best_server()

if remote_ip is not None:
    main()
