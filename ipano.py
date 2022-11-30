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


class BadParameter(Exception):
    def __init__(self, message, value=None):
        self.value = value
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        if self.value is None:
            return self.mesage
        else:
            return f"[{self.value}] {self.message}"


def _fmt(val, length, precision=0, sign=False):
    if sign:
        s = "-" if val < 0 else "+"
        val = abs(val)
    else:
        s = ""

    val *= 10**precision

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

    def __str__(self):
        return f"iPANO serial interface: {self._serial.name}"

    def __del__(self):
        self._serial.close()

    def _communicate(self, instruction, data="", output=True):
        data = "".join(str(d) for d in data)
        if len(instruction) != 3:
            raise BadParameter(
                "Instruction must be a 3 character sequence.", instruction
            )
        if len(data) > 33:
            raise BadParameter("Data must be at most 33 chars.", len(data))

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
            raise BadParameter("Axis must be None, 'alt' or 'az'.", axis)

    def goto(self, alt, az):
        if alt < -180 or alt > 180:
            raise BadParameter("Altitude must be in [-180, 180] range.", alt)
        if az < 0 or az > 360:
            raise BadParameter("Azimuth must be in the [0, 360] range.", az)

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
            raise BadParameter("ID can only be 0 or 2.", id)

    def start_panorama(self, mode: PANORAMA_MODE, id: Union[POSITION, IMAGING_PATH]):
        self._communicate("SPA", [mode.value, id.value])

    def set_timelapse(self, N, ang=0.0):
        self._communicate("STL", [0, _fmt(N, 5)])
        self._communicate("STL", [1, _fmt(ang, 3, 1, sign=True)])

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
        res = self._communicate("GRE")
        return PANORAMA_MODE(res)

    def get_progress(self):
        res = self._communicate("GPG")
        return int(res[:5]), int(res[5:])

    def battery(self):
        res = self._communicate("GPW")
        return int(res)
