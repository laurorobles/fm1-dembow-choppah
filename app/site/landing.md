# CHOPPAH DEMBOW

**Español:**
**CHOPPAH DEMBOW** es una versión personalizada de [CHOPPAH](https://github.com/profikid/fm1-break-choppah) (firmware original de Laurens Profittlich) diseñada para convertir el **M-VAVE FM-1** en un *chopper* de **Dembow**: 16 *slices* en las teclas blancas, *pads* momentáneos en las teclas negras (rolls, reverse, freeze, half speed, tape stop, gate), generador rítmico en vivo, cadena de efectos master (filtro, crunch, drive, punch, flanger, ring mod, tremolo, reverb, ping-pong delay, EQ, tape, compresor multibanda, clipper), 16 patrones con secuenciador por pasos, kick/snare/hi-hat y audio/MIDI por Bluetooth.

**Qué cambia respecto al CHOPPAH original:**
- **Librería personalizada de Dembow (7 loops):** `DB 104 A`, `DB 104 B`, `DB OCHOSI`, `DB TIBURON`, `DB TINYTUNE`, `DB MJ 21`, `DB MJ 97` (optimizados y nivelados a `-16 dBFS` con `tools/dembow_convert.py` para respetar el búfer del FM-1 incluso en tempos de `90–97 BPM`).
- **Continuous Play opcional (`CONT PLAY`):** en **LFO → GROOVE → K3**, puedes alternar entre **ON** (comportamiento original: el loop sigue corriendo) y **OFF** (cada *slice* o tecla se detiene al final de su corte para *chops* secos de dembow).

---

**English:**
**CHOPPAH DEMBOW** is a custom version of [CHOPPAH](https://github.com/profikid/fm1-break-choppah) (original firmware by Laurens Profittlich) tailored to turn the **M-VAVE FM-1** into a **Dembow chopper**: 16 slices on the white keys, momentary effect pads on the black keys, live rhythm generator, master FX chain, 16-pattern step sequencer, kick/snare/hi-hat, and Bluetooth audio/MIDI.

**Differences from original CHOPPAH:**
- **Custom Dembow Break Bank (7 loops):** `DB 104 A`, `DB 104 B`, `DB OCHOSI`, `DB TIBURON`, `DB TINYTUNE`, `DB MJ 21`, `DB MJ 97` (optimized and leveled to `-16 dBFS` via `tools/dembow_convert.py` to fit the FM-1 buffer even at `90–97 BPM`).
- **Optional Continuous Play (`CONT PLAY`):** under **LFO → GROOVE → K3**, toggle between **ON** (original behavior: slices run on into the loop) and **OFF** (each slice/key stops cleanly at its boundary for tight dembow chops).

![CHOPPAH DEMBOW playing: the break's waveform with the slice sounding lit, sixteen slice blocks below, the pads and the knobs](manual/img/screen-slicer.png "CHOPPAH DEMBOW slicer view")

Version {{VERSION}}. Installing is at your own risk; the installer can put M-VAVE's own firmware back.

- [Try it in the browser / Probar en el navegador](emu/): the same code the FM-1 runs, with sound. No FM-1 needed.
- [Install / Instalar (1-click)](install/): from Chrome or Edge, with the FM-1 connected by USB.
- [Manual](manual/): the slicer, the pads, the patterns, the effects, the drums.
- [Download / Descargar {{PKG}}](firmware/{{PKG}}): for the command-line installer, `python3 tools/fm1_install.py {{PKG}}`.

Based on CHOPPAH by Laurens Profittlich. Built on fm1-base and felucca-bsp, from Felucca by Leo Kuroshita, Hügelton Instruments. MPL-2.0.
M-VAVE and FM-1 are trademarks of their owners. CHOPPAH DEMBOW is not affiliated with M-VAVE.
