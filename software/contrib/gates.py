"""
Bill Gates
author: Adam Wonak (github.com/awonak)
date: 2022-04-24
labels: sequencer, gates, triggers, random

Inspired by Varigate, 16-step trigger/gate sequencer with probability
and retriggers.

Modes: pattern select, rotate

Attributes: trigger on/off, probability, re-trig


digital_in: clock in
analog_in:

knob_1: select step in current pattern
knob_2: adjust the value of the selected attribute

button_1:
    short: cycle through editable parameters (probability, retrigger, pitch cv)
button_2:
    short: cycle through patterns
    long: reset all patterns

output_1: trigger/gate pattern 1
output_2: trigger/gate pattern 2
output_3: trigger/gate pattern 2
output_4: pitch cv 1
output_5: pitch cv 2
output_6: pitch cv 3

"""
import uasyncio as asyncio

from random import random
from time import ticks_diff, ticks_ms

try:
    # Local development
    from software.firmware.europi import OLED_WIDTH, OLED_HEIGHT, CHAR_HEIGHT
    from software.firmware.europi import Output
    from software.firmware.europi import b1, b2, cv1, cv2, cv3, din, k1, k2, oled
    from software.firmware.europi_script import EuroPiScript
except ImportError:
    # Device import path
    from europi import *
    from europi_script import EuroPiScript


MENU_DURATION = 1200
TRIGGER_MS = 5


class Pattern:
    def __init__(self, cv: Output, steps: int):
        # TODO: Implement load/save state.
        self.cv = cv
        self.probability = [0] * steps
        self.retrig = [0] * steps
        self.steps = steps
        self.current_step = -1

        # Configurable behavior
        self._prob_precision = 101  # full 0 to 100 range
        self._max_retrig = 8

    def edit_prob(self, step: int, value: float):
        self.probability[step] = value

    def edit_retrig(self, step: int, value: float):
        self.retrig[step] = value

    def get_probability(self, step: int):
        return int(self.probability[step] * self._prob_precision)

    def get_retrigs(self, step: int):
        return int(self.retrig[step] * self._max_retrig) + 1

    async def play_step(self, step, period):
        self.current_step = (self.current_step + 1) % self.steps
        if self.probability[step] >= random():
            retrigs = self.get_retrigs(step)
            duration = int(period / retrigs) - (TRIGGER_MS * retrigs)
            await self._trigger(self.cv, retrigs, duration)
        elif self.cv == cv1:
            print("MISS")

    async def _trigger(self, cv, retrigs, duration):
        for _ in range(retrigs):
            cv.on()
            await asyncio.sleep_ms(TRIGGER_MS)
            cv.off()
            await asyncio.sleep_ms(duration)


class BillGates(EuroPiScript):
    pages = ['Probability', 'Retrigger']

    def __init__(self, steps=8, run_length=16):
        # TODO: Implement load/save state.
        super().__init__()
        self.steps = steps
        self.current_step = 0
        self.page = 0
        self.current_pattern = 0

        self.STEP_WIDTH = int(OLED_WIDTH / self.steps)
        self.STEP_HEIGHT = OLED_HEIGHT - CHAR_HEIGHT

        self._prev_k2 = k2.range()
        # The number of captured observations of period duration between clock triggers.
        self._run_length = run_length
        # A list of clock trigger durations for calculating the moving average.
        self._run = [0] * run_length
        self._last_time = ticks_ms()
        # Current average duration between clock triggers.
        self._period = 0

        self.patterns = [
            Pattern(cv1, self.steps),
            Pattern(cv2, self.steps),
            Pattern(cv3, self.steps),
        ]

        din.handler(self.clock_in)

        self.page_button = b1
        self.page_button.handler(self.page_handler)

        self.pattern_button = b2
        self.pattern_button.handler(self.pattern_handler)

    @classmethod
    def display_name(cls):
        return "Bill Gates"

    def page_handler(self):
        self.page = (self.page + 1) % len(self.pages)

    def pattern_handler(self):
        self.current_pattern = (self.current_pattern + 1) % len(self.patterns)

    def clock_in(self):
        # Capture the duration between clock pulses for retriggers subdivision.
        current_period = ticks_diff(ticks_ms(), self._last_time)
        self._last_time = ticks_ms()
        self._run = self._run[1:] + [current_period]
        self._period = int(sum(self._run) / self._run_length)

        self.current_step = (self.current_step + 1) % self.steps

    def show_menu_header(self):
        '''Check if page or pattern button pressed to display header.'''
        if ticks_diff(ticks_ms(), self.page_button.last_pressed()) < MENU_DURATION:
            msg = f"{self.pages[self.page]}"
        elif ticks_diff(ticks_ms(), self.pattern_button.last_pressed()) < MENU_DURATION:
            msg = f"Pattern {self.current_pattern + 1}"
        else:
            return

        oled.fill_rect(0, 0, OLED_WIDTH, CHAR_HEIGHT, 1)
        oled.text(msg, 0, 0, 0)

    def edit(self, pattern, step):
        if self._prev_k2 != k2.range():
            self._prev_k2 = k2.range()

            if self.page == 0:  # Probability
                pattern.edit_prob(step, k2.percent())

            elif self.page == 1:  # Retrigger
                pattern.edit_retrig(step, k2.percent())
    
    def update_display(self, pattern, step):
        oled.fill(0)

        # Parameter page.
        if self.page == 0:  # Probability
            param = pattern.probability
            prob = pattern.get_probability(step)
            state = f"c:{step+1:<3} p:{prob:<3} s:{self.current_step+1:<3}"

        elif self.page == 1:  # Retrigger
            param = pattern.retrig
            retrig = pattern.get_retrigs(step)
            state = f"c:{step+1:<2} r:{retrig:<2} p:{self._period}"

        else:
            return

        # Parameter state display.
        oled.text(state, 0, 0, 1)

        # Vertical bar for each step of the current selected parameter.
        for i, p in enumerate(param):
            x1 = (self.STEP_WIDTH * i) + 1
            y1 = OLED_HEIGHT - int(p * self.STEP_HEIGHT)
            x2 = self.STEP_WIDTH - 2
            y2 = (OLED_HEIGHT - y1) - 1
            oled.fill_rect(x1, y1, x2, y2, 1)

        # Box around current selected step.
        oled.rect(self.STEP_WIDTH * step, CHAR_HEIGHT,
                  self.STEP_WIDTH, self.STEP_HEIGHT-1, 1)

        # Display current step in sequence.
        oled.hline((self.STEP_WIDTH * self.current_step),
                   OLED_HEIGHT-1, self.STEP_WIDTH, 1)

        self.show_menu_header()
        oled.show()

    async def play_step(self):
        steps = []
        for p in self.patterns:
            if self.current_step != p.current_step:
                steps.append(p.play_step(self.current_step, self._period))
        if steps:
            await asyncio.gather(*steps)

    async def run(self):
        while True:
            await self.play_step()

            pattern = self.patterns[self.current_pattern]
            step = k1.range(self.steps)

            self.edit(pattern, step)
            self.update_display(pattern, step)

            # Release the semaphore for ample time allowing trigger tasks to run.
            await asyncio.sleep_ms(TRIGGER_MS)

    def main(self):
        asyncio.run(self.run())


if __name__ == "__main__":
    BillGates().main()
