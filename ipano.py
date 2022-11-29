import serial

# TODO: Add enums to clarify options

def _fmt(val,length,precision=0,sign=False):
    if sign:
        s = '-' if val < 0 else '+'
        val = abs(val)
    else:
        s = ""

    val *= 10**precision

    return f"{s}{int(val):0{length}}"

class IPANO:
    """Class for interfacing with the iPANO mount through the serial interface."""

    # Serial communication

    def __init__(self,port):
        self._serial = serial.Serial(
            port=port,
            baudrate=115200,
            bytesize=8,
            parity='N',
            stopbits=1,
            xonxoff=False
        )

    def _communicate(self,instruction,data="",output=True):
        data = ''.join(str(d) for d in data)
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
        return res[:6],res[6:]

    def mount_type(self):
        return self._communicate("INF")


    # Motion

    def move(self,dir):
        if dir not in "lrud":
            raise ValueError(
                f"Unknown direction: '{dir}'. Must be one of 'u', 'd', 'l' or 'r'."
            )
        self._communicate(f"mv{dir}",output=False)
        
    def stop(self,axis=None):
        if axis is None or axis.lower() == "none":
            self._communicate("mqq")
        elif axis.lower() == "az":
            self._communicate("qAZ")
        elif axis.lower() == "alt":
            self._communicate("qAL")
        else:
            raise ValueError("axis must be None, 'alt' or 'az'.")

    def goto(self,alt,az):
        self._communicate("SSL",[_fmt(alt,5,2,sign=True),_fmt(az,5,2)])


    # Set and Operation

    def shutter_test(self):
        self._communicate("SHT")

    def goto_zero_position(self):
        self._communicate("SPZ","0")

    def set_zero_position(self):
        self._communicate("SPZ","1")

    def set_reference_point(self,id):
        if id == 0:
            self._communicate("SOP","0")
        elif id == 2:
            self._communicate("SOP","1")
        else:
            raise ValueError("id can only be 0 or 2.")  

    def start_panorama(self,mode,id):
        self._communicate("SPA",f"{mode}{id}")

    def set_timelapse(self,N,ang=0.):
        self._communicate("STL",f"0{N:05}")
        self._communicate("STL",f"1{'-' if ang < 0 else '+'}{int(abs(ang)/10):03}")

    def get_step(self):
        res = self._communicate("GTL")
        return float(res[:6]),float(res[6:])

    def set_timing(self,mode,seconds):
        self._communicate("STT",f"{mode}{int(seconds):07}")

    def get_timing(self,mode):
        res = self._communicate("GTT",str(mode))
        return int(res)

    def shooting_control(self,cmd):
        self._communicate("SPC",str(cmd))

    def status(self):
        res = self._communicate("GAS")
        alt = float(res[:6]) / 100
        az = float(res[6:-1]) / 100
        mode = res[-1]
        return alt,az,mode

    def set_fov(self,fov):
        self._communicate("SFV",_fmt(fov,4,1))

    def get_fov(self):
        res = self._communicate("GFV")
        return float(res) / 10

    def repeat_last(self):
        self._communicate("SRE")

    def check_last(self):
        return self._communicate("GRE")

    def get_progress(self):
        res = self._communicate("GPG")
        return int(res[:5]),int(res[5:])

    def battery(self):
        res = self._communicate("GPW")
        return int(res)
