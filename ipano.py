from enum import Enum
from typing import Union

import serial


class DIRECTION(Enum):
    LEFT = "l"
    RIGHT = "r"
    UP = "u"
    DOWN = "d"


class POSITION(Enum):
    UPPER_LEFT = "0"
    LOWER_LEFT = "1"
    LOWER_RIGHT = "2"
    UPPER_RIGHT = "3"
    CENTER = "4"


class IMAGING_PATH(Enum):
    HORIZONTAL_ALTERNATING_DOWN = "0"
    HORIZONTAL_ALTERNATING_UP = "1"
    VERTICAL_ALTERNATING_RIGHT = "2"
    VERTICAL_ALTERNATING_LEFT = "3"
    HORIZONTAL_NONALTERNATING_DOWN = "4"
    HORIZONTAL_NONALTERNATING_UP = "5"
    VERTICAL_NONALTERNATING_RIGHT = "6"
    VERTICAL_NONALTERNATING_LEFT = "7"


class TIMING_PARAMETER(Enum):
    DELAYED_START = "0"
    TIME_INTERVAL = "1"
    TIME_LAPSE_TIME_INTERVAL = "2"


class SHOOTING_CONTROL(Enum):
    EXIT = "0"
    PAUSE = "1"
    RESUMING = "2"
    TIGGERING = "3"
    PREVIOUS = "4"
    NEXT = "5"


class STATUS(Enum):
    STOPPED = "0"
    MOVING = "1"
    WAITING = "2"
    DELAYING = "3"
    PAUSED = "4"
    SHOOTING = "5"


class PANORAMA_MODE(Enum):
    PREVIEW = "0"
    MATRIX = "1"
    THREE_SIXTY = "2"
    TIME_LAPSE = "3"


def _fmt(val, length, precision=0, sign=False):
    if sign:
        s = "-" if val < 0 else "+"
        val = abs(val)
    else:
        s = ""

    val *= 10 ** precision

    return f"{s}{int(val):0{length}}"


class IPANO:
    """Class for interfacing with the iPANO mount through the serial interface."""

    # Serial communication

    def __init__(self, port):
        self._serial = serial.Serial(
            port=port,
            baudrate=115200,
            bytesize=8,
            parity="N",
            stopbits=1,
            xonxoff=False,
        )

    def _communicate(self, instruction, data="", output=True):
        data = "".join(str(d) for d in data)
        if len(instruction) != 3:
            raise ValueError(
                f"instruction must be a 3 character sequence. Received '{instruction}'."
            )
        if len(data) > 33:
            raise ValueError(
                f"data must be at most 33 chars. Received length {len(data)} sequence: '{data}'."
            )

        message = f":01{instruction}{data}#"
        self._serial.write(message.encode())
        if output:
            response = ""
            while not response.endswith("#"):
                response += self._serial.read(self._serial.in_waiting).decode()
            return response[6:-1]

    # Firmware and type

    def firmware(self):
        res = self._communicate("FW0")
        return res[:6], res[6:]

    def mount_type(self):
        return self._communicate("INF")

    # Motion

    def move(self, dir: DIRECTION):
        self._communicate(f"mv{dir.value}", output=False)

    def stop(self, axis=None):
        if axis is None or axis.lower() == "none":
            self._communicate("mqq")
        elif axis.lower() == "az":
            self._communicate("qAZ")
        elif axis.lower() == "alt":
            self._communicate("qAL")
        else:
            raise ValueError("axis must be None, 'alt' or 'az'.")

    def goto(self, alt, az):
        self._communicate("SSL", [_fmt(alt, 5, 2, sign=True), _fmt(az, 5, 2)])

    # Set and Operation

    def shutter_test(self):
        self._communicate("SHT")

    def goto_zero_position(self):
        self._communicate("SPZ", "0")

    def set_zero_position(self):
        self._communicate("SPZ", "1")

    def set_reference_point(self, id):
        if id == 0:
            self._communicate("SOP", "0")
        elif id == 2:
            self._communicate("SOP", "1")
        else:
            raise ValueError("id can only be 0 or 2.")

    def start_panorama(
        self, mode: PANORAMA_MODE, id: Union[POSITION, IMAGING_PATH]
    ):
        self._communicate("SPA", [mode.value, id.value])

    def set_timelapse(self, N, ang=0.0):
        self._communicate("STL", f"0{N:05}")
        self._communicate(
            "STL", f"1{'-' if ang < 0 else '+'}{int(abs(ang)/10):03}"
        )

    def get_step(self):
        res = self._communicate("GTL")
        return float(res[:6]), float(res[6:])

    def set_timing(self, mode: TIMING_PARAMETER, seconds):
        self._communicate("STT", [mode.value, _fmt(seconds, 7)])

    def get_timing(self, mode: TIMING_PARAMETER):
        res = self._communicate("GTT", mode.value)
        return int(res)

    def shooting_control(self, cmd: SHOOTING_CONTROL):
        self._communicate("SPC", cmd.value)

    def status(self):
        res = self._communicate("GAS")
        alt = float(res[:6]) / 100
        az = float(res[6:-1]) / 100
        mode = STATUS(res[-1])
        return alt, az, mode

    def set_fov(self, fov):
        self._communicate("SFV", _fmt(fov, 4, 1))

    def get_fov(self):
        res = self._communicate("GFV")
        return float(res) / 10

    def repeat_last(self):
        self._communicate("SRE")

    def check_last(self):
        return self._communicate("GRE")

    def get_progress(self):
        res = self._communicate("GPG")
        return int(res[:5]), int(res[5:])

    def battery(self):
        res = self._communicate("GPW")
        return int(res)
