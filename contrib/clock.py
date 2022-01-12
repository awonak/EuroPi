from europi import *
from time import ticks_diff, ticks_add, ticks_ms, sleep_ms
import machine

machine.freq(250000000)

# Internal clock tempo range.
MAX_BPM = 280
MIN_BPM = 20

# Number of sequential reads for smoothing analog read values.
SAMPLES = 32


class Clock:
    internal_clock = True

    _deadline = 0
    _period = 0
    _prev_clock = 0
    _last_time = 0

    def __init__(self, knob):
        self.knob = knob

    @property
    def tempo(self):
        """Read the current tempo set by given knob within set range."""
        if self.internal_clock:
            return round(self.knob.read_position(MAX_BPM - MIN_BPM, SAMPLES) + MIN_BPM)
        else:
            return int((60 * 1000) / self._period)

    def _get_next_deadline(self):
        self._period = int((60 / self.tempo) * 1000)
        return ticks_add(ticks_ms(), int(self._period / 4))  # 4 PPQN

    def _internal_wait(self):
        while True:
            # Override internal clock if external clock pulse detected.
            if din.value() == 1:
                self.internal_clock = False
                self._last_time = ticks_ms()
                self._prev_clock = 1
                return
            # Internal clock wait.
            if ticks_diff(self._deadline, ticks_ms()) <= 0:
                self._deadline = self._get_next_deadline()
                return

    def _external_wait(self):
        while True:
            # Override external clock if no pulse for 3 seconds.
            self._period = ticks_diff(ticks_ms(), self._last_time) * 4  # 4 PPQN
            if self._period > 3000:
                self.internal_clock = True
                return
            # External clock wait.
            if din.value() != self._prev_clock:
                self._prev_clock = 1 if self._prev_clock == 0 else 0
                if self._prev_clock == 0:
                    self._last_time = ticks_ms()
                    return

    def wait(self):
        """Wait for a clock cycle of the current selected clock source."""
        if self.internal_clock:
            self._internal_wait()
        else:
            self._external_wait()
    
    def display(self):
        """Display clock source, tempo and period."""
        source = "internal" if self.internal_clock else "external"
        oled.centre_text(f"source: {source}\ntempo: {self.tempo:>3} BPM\nperiod: {self._period:>4} ms")

    def main(self):
        while True:
            # Display clock state
            self.display()
            # Clock trigger
            cv1.on()
            sleep_ms(5)
            cv1.off()
            # Wait for next clock cycle
            self.wait()


if __name__ == '__main__':
    c = Clock(k1)
    c.main()
