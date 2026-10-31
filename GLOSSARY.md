# Glossary

Terms for the cook-temperature dashboard that combines a BLE thermometer base with a 433 MHz radio probe.

## Language

**BLE base**:
The ChefsTemp / ProTemp S1 unit that reports one probe temperature and a battery level over Bluetooth Low Energy.
_Avoid_: S1, ChefsTemp, ProTemp, wireless probe

**Radio probe**:
The 433 MHz thermometer that `rtl_433` decodes as `Thermopro-TP12`. It reports two temperatures per reading.
_Avoid_: TP12, TempPro, ProTemp1, wireless probe

**Food**:
The radio probe channel for the probe inside the food ("Temperature 1 (Food)").
_Avoid_: meat, probe 1

**Pit**:
The radio probe channel for the cooking-chamber temperature ("Temperature 2 (Barbecue)").
_Avoid_: barbecue, ambient, probe 2

**BLE food**:
The single probe temperature that the BLE base reports.
_Avoid_: S1 temperature

**Unplugged**:
A radio probe channel that reads the placeholder value (about 320 °C / 608 °F) because no probe is connected.
_Avoid_: error, offline

**No signal**:
A gauge state meaning its source has sent no recent reading, shown with the time since the last one.
_Avoid_: disconnected, dead

**Target**:
The temperature a user sets for a gauge. The app estimates the time to reach it.
_Avoid_: setpoint, alarm

**Cook**:
One recorded session of readings from all sources, saved to a file and replayable.
_Avoid_: run, session
