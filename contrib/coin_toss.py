from europi import *
from clock import Clock
from random import random
from time import sleep_ms
import machine


# Constant values for display.
FRAME_WIDTH = int(OLED_WIDTH / 8)

# Number of sequential reads for smoothing analog read values.
SAMPLES = 32

# Overclock the Pico for improved performance.
machine.freq(250000000)
# machine.freq(125000000)  # Default clock speed.


class CoinToss:
    DISPLAY_MODES = ['COIN1', 'COIN2', 'CLOCK']

    def __init__(self, clock=Clock(k1)):
        self.clock = clock
        self.gate_mode = True
        self.display_mode = 0

        @b1.handler
        def toggle_display():
            self.display_mode = (self.display_mode + 1) % len(self.DISPLAY_MODES)
            oled.clear()
            oled.show()

        @b2.handler
        def toggle_gate():
            """Toggle between gate and trigger mode."""
            self.gate_mode = not self.gate_mode
            [o.off() for o in cvs]

    def toss(self, a, b, draw=True):
        """If random value is below trigger a, otherwise trigger b.

        If draw is true, then display visualization of the coin toss.
        """
        coin = random()
        # Sum the knob2 and analogue input values to determine threshold.
        read_sum = k2.unit_interval(SAMPLES) + ain.read_voltage(SAMPLES)/12
        self.threshold = clamp(read_sum, 0, 1)
        if self.gate_mode:
            a.value(coin < self.threshold)
            b.value(coin > self.threshold)
        else:
            (a if coin < self.threshold else b).on()
        
        if not draw:
            return

        # Draw gate/trigger display graphics for coin toss
        h = int(self.threshold * OLED_HEIGHT)
        tick = FRAME_WIDTH if self.gate_mode else 1
        offset = 8  # The amount of negative space before drawing gate.
        if coin < self.threshold:
            oled.fill_rect(offset, 0, tick, h, 1)
        else:
            oled.fill_rect(offset, h, tick, OLED_HEIGHT, 1)

    def main(self):
        # Start the main loop.
        counter = 0
        while True:
            # Random coin toss for each coin pair.
            self.toss(cv1, cv2, self.display_mode == 0)
            cv3.on()  # First column clock trigger

            if counter % 4 == 0:
                self.toss(cv4, cv5, self.display_mode == 1)
                cv6.on()  # Second column clock trigger (1/4x speed)
            
            sleep_ms(10)
            if self.gate_mode:
                # Only turn off clock triggers.
                [o.off() for o in (cv3, cv6)]
            else:
                # Turn of all cvs in trigger mode.
                [o.off() for o in cvs]

            # Display state
            if self.display_mode == 2:
                self.clock.display()
            else:
                # Draw threshold line
                oled.hline(0, int(self.threshold * OLED_HEIGHT), FRAME_WIDTH, 1)
                oled.show()
                # Scroll and clear new screen area.
                oled.scroll(FRAME_WIDTH, 0)
                oled.fill_rect(0, 0, FRAME_WIDTH, OLED_HEIGHT, 0)

            counter += 1
            self.clock.wait()


if __name__ == '__main__':
    # Reset module display state.
    [o.off() for o in cvs]
    oled.clear()
    oled.show()

    coin_toss = CoinToss()
    coin_toss.main()
