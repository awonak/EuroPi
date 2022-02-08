try:
    # Local development
    from software.firmware.europi import ain, din, cvs, oled
except ImportError:
    # Device import path
    from europi import *
from time import sleep_ms
import machine



NOTES = [
    "C0", "C#0", "D0", "D#0", "E0", "F0", "F#0", "G0", "G#0", "A0", "A#0", "B0",
    "C1", "C#1", "D1", "D#1", "E1", "F1", "F#1", "G1", "G#1", "A1", "A#1", "B1",
    "C2", "C#2", "D2", "D#2", "E2", "F2", "F#2", "G2", "G#2", "A2", "A#2", "B2",
    "C3", "C#3", "D3", "D#3", "E3", "F3", "F#3", "G3", "G#3", "A3", "A#3", "B3",
    "C4", "C#4", "D4", "D#4", "E4", "F4", "F#4", "G4", "G#4", "A4", "A#4", "B4",
]


VOLT_PER_OCT = 1 / 12


class Chord:
    def __init__(self):
        self.notes = []
        self.voltages = []
        self._previous_voltage = 0

        @din.handler_falling
        def gate_off():
            self.notes = []
            self.voltages = []
            self._previous_voltage = -1
            self.display()

    def voltage_to_note(self, voltage):
        return NOTES[int(voltage * 12) - 1]
    
    def display(self):
        notes = " ".join(self.notes)
        oled.centre_text(f"Chord:\n{notes}")
    
    def read_keys(self):
        voltage = ain.read_voltage(samples=1024)
        if abs(voltage - self._previous_voltage) > 0.05:
            self.voltages.append(voltage)
            self.notes.append(self.voltage_to_note(voltage))
            self.display()
        self._previous_voltage = voltage
    
    def play_notes(self):
        for cv, voltage in zip(cvs, self.voltages):
            cv.voltage(voltage)
    
    def main(self):
        while True:
            if din.value() == 1:
                self.read_keys()
                self.play_notes()
            
            sleep_ms(200)


if __name__ == '__main__':
    chord = Chord()
    chord.main()
