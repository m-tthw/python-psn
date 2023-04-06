#!/bin/env python3

import socket
from struct import unpack
from enum import IntEnum
from typing import List
import os
from threading import Thread


class psn_vector3:
    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z

    def __str__(self):
        return f"{self.x}, {self.y} {self.z}"

    def __eq__(self, other) -> bool:
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __iter__(self):
        return iter((self.x, self.y, self.z))


class psn_info:
    def __init__(
        self,
        timestamp: int,
        version_high: int,
        version_low: int,
        frame_id: int,
        packet_count: int,
    ):
        self.timestamp = timestamp
        self.version_high = version_high
        self.version_low = version_low
        self.frame_id = frame_id
        self.packet_count = packet_count


class psn_tracker_info:
    def __init__(self, tracker_id: int, tracker_name: str):
        self.tracker_id = tracker_id
        self.tracker_name = tracker_name


class psn_tracker:
    def __init__(
        self,
        id: int,
        info: "psn_info" = None,
        pos: "psn_vector3" = None,
        speed: "psn_vector3" = None,
        ori: "psn_vector3" = None,
        accel: "psn_vector3" = None,
        trgtpos: "psn_vector3" = None,
        status: int = 0,
        timestamp: int = 0,
    ):
        self.id = id
        self.info = info
        self.pos = pos
        self.speed = speed
        self.ori = ori
        self.accel = accel
        self.trgtpos: psn_vector3 = trgtpos
        self.status = status
        self.timestamp = timestamp


class psn_data_packet:
    def __init__(self, info: "psn_info", trackers: List["psn_tracker"]):
        self.info = info
        self.trackers = trackers


class psn_info_packet:
    def __init__(
        self,
        info: "psn_info",
        name: str,
        trackers: List["psn_tracker_info"],
    ):
        self.info = info
        self.name = name
        self.trackers = trackers


class psn_v1_chunk(IntEnum):
    PSN_V1_INFO_PACKET = 0x503C
    PSN_V1_DATA_PACKET = 0x6754


class psn_v2_chunk(IntEnum):
    PSN_INFO_PACKET = 0x6756
    PSN_DATA_PACKET = 0x6755


class psn_info_chunk(IntEnum):
    PSN_INFO_PACKET_HEADER = 0x0000
    PSN_INFO_SYSTEM_NAME = 0x0001
    PSN_INFO_TRACKER_LIST = 0x0002


class psn_data_chunk(IntEnum):
    PSN_DATA_PACKET_HEADER = 0x0000
    PSN_DATA_TRACKER_LIST = 0x0001


class psn_tracker_list_chunk(IntEnum):
    PSN_INFO_TRACKER_NAME = 0x0000


class psn_tracker_chunk(IntEnum):
    PSN_DATA_TRACKER_POS = 0x0000
    PSN_DATA_TRACKER_SPEED = 0x0001
    PSN_DATA_TRACKER_ORI = 0x0002
    PSN_DATA_TRACKER_ACCEL = 0x0004
    PSN_DATA_TRACKER_TRGTPOS = 0x0005


class psn_tracker_chunk_info(IntEnum):
    PSN_DATA_TRACKER_STATUS = 0x0003
    PSN_DATA_TRACKER_TIMESTAMP = 0x0006


def join_multicast_win(MCAST_GRP, MCAST_PORT, if_ip):
    mcastsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    mcastsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    mcastsock.setsockopt(
        socket.SOL_IP,
        socket.IP_ADD_MEMBERSHIP,
        socket.inet_aton(MCAST_GRP) + socket.inet_aton(if_ip),
    )
    mcastsock.bind(("", MCAST_PORT))
    return mcastsock


def join_multicast_linux(MCAST_GRP, MCAST_PORT, if_ip):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except Exception as e:
        print(e)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)

    sock.bind((MCAST_GRP, MCAST_PORT))
    print(socket.gethostname())
    host = socket.gethostbyname(socket.gethostname())
    host = if_ip
    print(host)
    sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(host))
    sock.setsockopt(
        socket.SOL_IP,
        socket.IP_ADD_MEMBERSHIP,
        socket.inet_aton(MCAST_GRP) + socket.inet_aton(host),
    )
    return sock


def determine_os():
    if os.name == "nt":
        return "Operating system not supported"
        # return str(os.name)

    elif os.name == "posix":
        return str(os.name)

    else:
        return "Operating system not supported"


class receiver(Thread):
    def __init__(self, callback, ip_addr):
        Thread.__init__(self)
        self.callback = callback
        self.socket = init(ip_addr)

    def run(self):
        data = ""
        if self.socket is None:
            return
        while 1:
            try:
                data, addr = self.socket.recvfrom(1024)
            except Exception as e:
                print(e)
            else:
                psn_data = parse_psn_packet(data)
                if isinstance(psn_data, psn_data_packet):
                    print(psn_data.trackers[0].pos)
                    self.callback(psn_data)


def init(ip_addr):
    MCAST_GRP = "236.10.10.10"
    MCAST_PORT = 56565
    IP_ADDR = ip_addr
    sock = None
    if determine_os() == "nt":
        sock = join_multicast_win(MCAST_GRP, MCAST_PORT, IP_ADDR)
    elif determine_os() == "posix":
        sock = join_multicast_linux(MCAST_GRP, MCAST_PORT, IP_ADDR)

    if sock is None:
        print("error getting network interface")
        return
    return sock


def parse_psn_packet(buffer):
    psn_id = unpack("<H", buffer[0:2])[0]
    if psn_id in iter(psn_v1_chunk):
        pass  # PSN V1 not supported by this parser
    elif psn_id in iter(psn_v2_chunk):
        chunk_id, chunk_buffer, rest = parse_chunk(buffer)
        if chunk_id == psn_v2_chunk.PSN_INFO_PACKET:
            parse_info(chunk_buffer)
        elif chunk_id == psn_v2_chunk.PSN_DATA_PACKET:
            return parse_data(chunk_buffer)


def parse_chunk(buffer):
    chunk_id, data_field = unpack("<HH", buffer[0:4])
    data_len = data_field & 0x7FFF
    data = buffer[4 : 4 + data_len]
    rest = None

    if data_len + 8 < len(buffer):
        rest = buffer[data_len + 4 :]
    return chunk_id, data, rest


def parse_info(buffer):
    print("parsing info", len(buffer))
    while buffer:
        chunk_id, chunk_buffer, buffer = parse_chunk(buffer)
        if chunk_id == psn_info_chunk.PSN_INFO_PACKET_HEADER:
            parse_header(chunk_buffer)
        elif chunk_id == psn_info_chunk.PSN_INFO_SYSTEM_NAME:
            parse_system_name(chunk_buffer)
        elif chunk_id == psn_info_chunk.PSN_INFO_TRACKER_LIST:
            parse_info_tracker_list(chunk_buffer)


def parse_data(buffer):
    # print("parsing data", len(buffer))
    while buffer:
        chunk_id, chunk_buffer, buffer = parse_chunk(buffer)
        if chunk_id == psn_data_chunk.PSN_DATA_PACKET_HEADER:
            # print("got data header")
            info = parse_header(chunk_buffer)
        elif chunk_id == psn_data_chunk.PSN_DATA_TRACKER_LIST:
            # print("got tracker list", len(chunk_buffer))
            trackers = parse_data_tracker_list(chunk_buffer)
    packet = psn_data_packet(info, trackers)
    return packet


def parse_header(buffer):
    # print("parsing header", len(buffer))

    timestamp, version_high, version_low, frame_id, packet_count = unpack(
        "<LHHHH", buffer
    )
    info = psn_info(timestamp, version_high, version_low, frame_id, packet_count)
    # print(timestamp, version_high, version_low, frame_id, packet_count)
    return info


def parse_system_name(buffer):
    # print("parsing system name", len(buffer))
    # TODO: may cause unicode issues?
    system_name = buffer
    # print("SYSTEM NAME", system_name)


def parse_info_tracker_list(buffer):
    # print("parsing info tracker list", len(buffer))
    while buffer:
        tracker_id, chunk_buffer, buffer = parse_chunk(buffer)

        # print(hex(tracker_id))

        if len(chunk_buffer) > 0:
            while chunk_buffer:
                chunk_id, info_buffer, chunk_buffer = parse_chunk(chunk_buffer)
                if chunk_id == psn_tracker_list_chunk.PSN_INFO_TRACKER_NAME:
                    # TODO: encoding issues?
                    tracker_name = info_buffer
                    # print(tracker_name)


def parse_data_tracker_list(buffer):
    # print("parsing data tracker list", len(buffer))
    trackers: List["psn_tracker"] = []
    while buffer:
        tracker_id, chunk_buffer, buffer = parse_chunk(buffer)

        tracker = psn_tracker(tracker_id)
        # print(hex(tracker_id))

        if len(chunk_buffer) > 0:
            while chunk_buffer:
                chunk_id, info_buffer, chunk_buffer = parse_chunk(chunk_buffer)
                if chunk_id in iter(psn_tracker_chunk):
                    vector = psn_vector3(*unpack("<fff", info_buffer))
                    # print(tracker_chunk(chunk_id).name, x, y, z)
                    if chunk_id == psn_tracker_chunk.PSN_DATA_TRACKER_POS:
                        tracker.pos = vector
                    elif chunk_id == psn_tracker_chunk.PSN_DATA_TRACKER_ORI:
                        tracker.ori = vector
                    elif chunk_id == psn_tracker_chunk.PSN_DATA_TRACKER_ACCEL:
                        tracker.accel = vector
                    elif chunk_id == psn_tracker_chunk.PSN_DATA_TRACKER_SPEED:
                        tracker.speed = vector
                    elif chunk_id == psn_tracker_chunk.PSN_DATA_TRACKER_TRGTPOS:
                        tracker.trgtpos = vector

                elif chunk_id == psn_tracker_chunk_info.PSN_DATA_TRACKER_STATUS:
                    status = unpack("<f", info_buffer)[0]
                    tracker.status = status
                    # print(tracker_chunk_info(chunk_id).name, status)
                elif chunk_id == psn_tracker_chunk_info.PSN_DATA_TRACKER_TIMESTAMP:
                    timestamp = unpack("<L", info_buffer)[0]
                    tracker.timestamp = timestamp
                    # print(tracker_chunk_info(chunk_id).name, timestamp)
        trackers.append(tracker)
    return trackers
