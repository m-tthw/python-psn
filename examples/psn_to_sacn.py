#! /bin/env python
import sacn
import pypsn

# Note: not tested

sender = sacn.sACNsender()


def start_dmx():
    sender.start()  # start the sending thread
    sender.activate_output(1)  # start sending out data in the 1st universe
    sender[1].multicast = True  # set multicast to True


def stop_dmx():
    sender.stop()  # do not forget to stop the sender


def start_psn():
    pypsn.receiver(fill_dmx, "192.168.20.177").start()


def fill_dmx(psn_data):
    dmx = psn_data.trackers[0].pos
    dmx_data = [0] * 512
    dmx_data[0] = int(abs(dmx.x))
    dmx_data[1] = int(abs(dmx.y))
    dmx_data[2] = int(abs(dmx.z))

    sender[1].dmx_data = dmx_data


if __name__ == "__main__":
    start_dmx()
    start_psn()
