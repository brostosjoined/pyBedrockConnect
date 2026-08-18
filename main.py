import socket
import struct
import select

HOST = "0.0.0.0"
PORT = 19132

REMOTE_IP = "104.238.130.180"
REMOTE_PORT = 19132

BUFFER_SIZE = 65535

MAGIC = bytes.fromhex("00 ff ff 00 fe fe fe fe fd fd fd fd 12 34 56 78")

SERVER_GUID = 0x7165B97802C172E1

SERVER_NAME = (
    "MCPE;"
    "Python Proxy;"
    "2168;"
    "1.26.44;"
    "0;"
    "10;"
    "0;"
    "Python World;"
    "survival;"
    "1;"
    "19132;"
    "19132"
).encode("utf-8")


def hex_dump(data):
    return data.hex(" ")


def build_offline_pong(client_timestamp):
    return (
        b"\x1c"
        + struct.pack(">Q", client_timestamp)
        + struct.pack(">Q", SERVER_GUID)
        + MAGIC
        + struct.pack(">H", len(SERVER_NAME))
        + SERVER_NAME
    )


def print_packet(title, data, addr):
    packet_id = data[0] if data else 0

    print()
    print("-" * 70)
    print(title)
    print(f"From:   {addr}")
    print(f"Length: {len(data)} bytes")
    print(f"ID:     0x{packet_id:02X}")
    print(f"Data:   {hex_dump(data)}")
    print("-" * 70)


def main():

    # ---------------------------------------------------------
    # LAN socket
    # ---------------------------------------------------------

    lan_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    lan_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    lan_socket.bind((HOST, PORT))

    # ---------------------------------------------------------
    # Remote server socket
    # ---------------------------------------------------------

    remote_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    remote_server = (REMOTE_IP, REMOTE_PORT)

    client_addr = None

    print("=" * 70)
    print("RakNet LAN Proxy")
    print("=" * 70)
    print(f"LAN listening:   {HOST}:{PORT}")
    print(f"Remote server:   {REMOTE_IP}:{REMOTE_PORT}")
    print(f"Server GUID:     {SERVER_GUID}")
    print(f"Server name:     {SERVER_NAME.decode()}")
    print("=" * 70)
    print()
    print("[READY] Waiting for LAN client...")
    print()

    while True:

        try:

            readable, _, _ = select.select([lan_socket, remote_socket], [], [])

        except KeyboardInterrupt:
            print("\nStopping...")
            break

        except Exception as e:
            print(f"[ERROR] select(): {e}")
            continue

        for sock in readable:

            # =================================================
            # LAN CLIENT -> PROXY
            # =================================================

            if sock is lan_socket:

                try:
                    data, addr = lan_socket.recvfrom(BUFFER_SIZE)

                except Exception as e:
                    print(f"[ERROR] LAN recvfrom(): {e}")
                    continue

                print_packet("[LAN -> PROXY]", data, addr)

                if not data:
                    print("[IGNORED] Empty packet")
                    continue

                packet_id = data[0]

                # -------------------------------------------------
                # Offline Ping
                # -------------------------------------------------

                if packet_id == 0x01:

                    print("[RAKNET] Offline Ping detected")

                    if len(data) < 33:
                        print("[WARNING] Offline Ping is too short")
                        continue

                    client_timestamp = struct.unpack(">Q", data[1:9])[0]

                    received_magic = data[9:25]

                    client_guid = struct.unpack(">Q", data[25:33])[0]

                    print(f"Client timestamp: {client_timestamp}")

                    print(f"Client GUID:      {client_guid}")

                    print(f"Magic:            " f"{hex_dump(received_magic)}")

                    if received_magic != MAGIC:

                        print("[WARNING] Invalid RakNet magic")

                        continue

                    print("[RAKNET] Magic is valid")

                    pong = build_offline_pong(client_timestamp)

                    print()
                    print("[SENDING OFFLINE PONG]")
                    print(f"To: {addr}")
                    print(f"Length: {len(pong)} bytes")
                    print(f"Data: {hex_dump(pong)}")

                    try:

                        sent = lan_socket.sendto(pong, addr)

                        print(f"[SENT] {sent} bytes")

                    except Exception as e:

                        print(f"[ERROR] Pong sendto(): {e}")

                    print("[SUCCESS] Offline Pong sent.")

                    continue

                # -------------------------------------------------
                # Everything else
                # -------------------------------------------------

                client_addr = addr

                print(f"[CLIENT] Active client: {client_addr}")

                print(
                    f"[RELAY] Forwarding "
                    f"0x{packet_id:02X} "
                    f"to {REMOTE_IP}:{REMOTE_PORT}"
                )

                try:

                    sent = remote_socket.sendto(data, remote_server)

                    print(f"[RELAY] Sent {sent} bytes " f"to remote server")

                except Exception as e:

                    print(f"[ERROR] Remote sendto(): {e}")

            # =================================================
            # REMOTE SERVER -> PROXY -> LAN CLIENT
            # =================================================

            elif sock is remote_socket:

                try:

                    data, addr = remote_socket.recvfrom(BUFFER_SIZE)

                except Exception as e:

                    print(f"[ERROR] Remote recvfrom(): {e}")

                    continue

                print_packet("[SERVER -> PROXY]", data, addr)

                if client_addr is None:

                    print(
                        "[WARNING] No LAN client is associated "
                        "with this server response"
                    )

                    continue

                packet_id = data[0] if data else 0

                print(
                    f"[RELAY] Forwarding "
                    f"0x{packet_id:02X} "
                    f"to LAN client {client_addr}"
                )

                try:

                    sent = lan_socket.sendto(data, client_addr)

                    print(f"[RELAY] Sent {sent} bytes " f"to LAN client")

                except Exception as e:

                    print(f"[ERROR] LAN sendto(): {e}")

    lan_socket.close()
    remote_socket.close()

    print("[STOPPED]")


if __name__ == "__main__":
    main()


