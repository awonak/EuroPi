"""
Clock

Author: Adam Wonak
Date: 2022/01/12

This script can be used as a standalone master clock or it can be imported by
other scripts and used as a master clock for that scripts.

When no cable is plugged into the digital input, this script will provide a 4
PPQN (pulse per quarternote) clock trigger on the given cv output. The Clock
will trigger every 16th note. The internal clock will provide a reliable and
(mostly*) steady clock within a range of 20 to ~300 BPM. The range should not
be too broad because when a larger the range is used, it becomes more difficult
to dial in a specific tempo with a single knob on the module.

When a cable is plugged into the digital input and a clock pulse is detected,
the Clock will switch to external clock mode and calculate the tempo based on
the period between pulses, expecting to receive 4 PPQN. If a pulse has not
been detected for a period greater than 3000 ms (20 BPM), then the Clock will
automatically switch back to internal clock source.

Other scripts can import the Clock to use as their own clock source. The Clock
can be initialized with either knob to control internal clock speed, and
optional cv output to emit the clock trigger. Additionally, the Clock has a
display method that shows the clock source, tempo and period. Scripts can use
the `wait()` method to block between clock cycles.

Sample script usage:

    from europi import *
    from time import sleep_ms
    from clock import Clock

    clock = Clock()

    while True:
        for output in cvs:
            # Trigger current output
            output.on()
            sleep_ms(10)
            output.off()
            # Block and wait for next clock cycle
            clock.wait()

*Note that clocks at higher tempos will start to loose accuracy caused by
Python's periodic garbage collection running and causing timing delays. The
Clock is mostly accurate within a range of 20 to 300 BPM for both internal and
external clock sources.

Run the script from rshell

    > repl ~ from main import * ~ c = Clock() ~ c.main()

"""
from europi import cv1, din, k1, oled
from time import ticks_diff, ticks_add, ticks_ms, sleep_ms


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

    def __init__(self, knob=k1, output=cv1):
        self.knob = knob
        self.output = output

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

    @property
    def tempo(self):
        """Read the current tempo set by given knob within set range."""
        if self.internal_clock:
            return round(self.knob.read_position(MAX_BPM - MIN_BPM, SAMPLES) + MIN_BPM)
        else:
            return int((60 * 1000) / self._period)

    @property
    def period(self):
        """The amount of time in ms between each quarter note clock pulse."""
        return self._period

    def wait(self):
        """Wait for a clock cycle of the current selected clock source."""
        if self.internal_clock:
            self._internal_wait()
        else:
            self._external_wait()

    def display(self):
        """Display clock source, tempo and period."""
        source = "internal" if self.internal_clock else "external"
        oled.centre_text(
            f"source: {source}\ntempo: {self.tempo:>3} BPM\nperiod: {self.period:>4} ms")

    def main(self):
        while True:
            # Display clock state
            self.display()
            # Clock trigger
            if self.output is not None:
                self.output.on()
                sleep_ms(5)
                self.output.off()
            # Wait for next clock cycle
            self.wait()


if __name__ == '__main__':
    c = Clock()
    c.main()