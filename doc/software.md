# Getting started with X1Plus Expander

This assumes that you have already [assembled the hardware](assembly.md).

## Installing a firmware

You will need to install an X1Plus firmware build that supports X1Plus
Expander.  Version 3.0 Release Candidate 1 is available for testing, but
until a full release happens that supports X1Plus Expander, this means that
you will need to manually upgrade, rather than using the on-board
over-the-air upgrade subsystem.

The currently recommended build is [3.0
rc1](https://github.com/X1Plus/X1Plus/releases/tag/x1plus%2F3.0_rc1). 
Download the `3.0_rc1.x1p`, put this in the root of your SD card,
and then restart your printer; on reboot, select "startup options", and then
"start X1Plus installer", and select it from the dropdown menu.

If you are running a firmware version that supports X1Plus Expander, you
should see "Expansion" appear in the "Hardware" tab, and if X1Plus Expander
is connected correctly and functioning properly, you should also see a
serial number appear underneath it.  You should also see "Wired Network"
appear in the "Network" tab if X1Plus Expander is connected and functioning.

## Connecting hardware to X1Plus Expander

X1Plus Expander port (the rectangular connectors on the top) are identified
by letters.  "B01" revisions of X1Plus Expander have only two functioning
ports -- the port on the left of X1Plus Expander (next to the I2C connector)
is "port B", and the connector two over from that is "port A".  (The port on
the right, and the port between port A and port B, are not usable in X1Plus
Expander B01; X1Plus Expander B01 hardware labels the usable ports in
silkscreen as "AD" and "BD".  All four ports will be usable in X1Plus
Expander revision C.) The leftmost port (port B, on revision B01) is always
shared with the STEMMA I2C connector.

It is better to power the printer off before connecting or disconnecting
add-on modules to the X1Plus Expander ports, but I can't stop you if you
really want to try it, and chances are good that you will probably get away
with it most of the time.

Add-on modules are not keyed right now.  Make sure that they are centered in
the port, and make sure that they face forward (i.e., that the arrow on the
add-on module matches up with the arrow on the port).

You can also connect other hardware to X1Plus Expander, using any standard
0.1" Dupont-style connector.  Doing so is outside of the scope of this
document, but if you get a hankering to do it, let me know what you are
trying to do and I will try to think up how you would do it, and document
it.

## Configuring X1Plus Expander

Currently, X1Plus Expander is primarily configured through the command line,
using the `x1plus settings` mechanism; a GUI to configure the ports is in
progress.  You can list all of X1Plus's settings with the `x1plus settings
get` command; conversely, you can also change settings with `x1plus settings
set`.  (You can run `x1plus settings set --help` to see exactly how it is
used.)

The settings keys for X1Plus Expander ports are `expansion.port_a` and
`expansion.port_b`, and should contain JSON objects that describe what is
connected to a port.  The exact format for these JSON objects is slightly in
flux, so for now, I'll provide recipes for setting up each supplied add-on
module:

### X1P-004 LED-strip level shifter module

Configure a port to drive an LED strip with:

```
# x1plus settings set expansion.port_x --json '{"ledstrip": {"leds": 10}}'
```

where "port_x" is correct for the port that you have plugged the X1P-004
into, and "10" has been changed to the correct number of LEDs in your LED
strip that you'd like to light up.  If you'd like to control which
animations are visible on your LED strip:

```
# x1plus settings set expansion.port_x --json '{"ledstrip": {"leds": 10, "animations": [{"running": {"brightness": 0.05}}, {"finish": {"brightness": 0.1}}]}}'
```

Available animations are `rainbow`, `paused`, `failed`, `running`, and
`finish`.  All animations take an optional `brightness` parameter (scaled
from 0 to 1); `failed` and `finish` also take an optional `timeout`
parameter (in seconds) to describe how long they should remain, before
returning to either a rainbow or a blank animation.

If you find it easier, you can also configure a port using a JSON or YAML
file, rather than having to input an entire JSON string in a command line
parameter.  For instance, you can do:

```
# cat > ledstrip.yaml <<EOF
ledstrip:
  animations:
  - running:
      brightness: 0.05
  - finish:
      brightness: 0.1
  leds: 10
EOF
# x1plus settings set expansion.port_x --file ledstrip.yaml --yaml
```

You may find this more convenient to experiment with.

TODO: document where to connect what for LED strips, and how to use an external power supply, if it is not obvious

### X1P-005 Andon module

An Andon module is just an LED strip module with 25 fixed LEDs on it, a
buzzer, and two buttons that serve as inputs.  This introduces the `gpio`
parameter to the `ledstrip` type of module.  I recommend a configuration for
X1P-005 that looks about as follows:

```
# x1plus settings set expansion.port_x --json '{"ledstrip": {"leds": 25, "gpios": [{"pin": 3, "function": "buzzer", "default": 0}, {"pin": 5, "default": 1}, {"pin": 6, "function": "button", "inverted": true}, {"pin": 7, "function": "button", "inverted": true}]}}'
```

You may also consider a YAML equivalent, if you wish to play with the
animations.  For instance, consider:

```
# cat > andon.yaml <<EOF
ledstrip:
  animations:
  - running:
      brightness: 0.05
  - rainbow:
      brightness: 0.1
  gpios:
  - pin: 3
    function: buzzer
    default: 0
  - pin: 5
    default: 1
  - pin: 6
    function: button
    inverted: true
  - pin: 7
    function: button
    inverted: true
  leds: 25
```

The Andon module will, by default, light up like any other LED strip.  To
use the buzzer or buttons, see the "Using X1Plus Actions" section, below.

### X1P-006 Shutter release module

A shutter release module is a GPIO module that has two outputs. 
Conveniently, the `ledstrip` driver can be used to drive GPIOs (the shutter
release module does not have anything connected to the LED output pin).  You
can configure a shutter release module as follows:

```
# x1plus settings set expansion.port_x --json '{"ledstrip": {"leds": 0, "gpios": [ { "pin": 3, "function": "shutter", "default": 0 }, { "pin": 5, "function": "shutter", "default": 0 } ] } }'
```

### Using I2C sensors

TODO: document `i2c` driver

## Using X1Plus Actions

X1Plus Actions is a new mechanism to trigger behavior from inside X1Plus. 
Actions are a commonized way to trigger tasks from the command line, from
G-code, or in response to various system events (including button presses). 
Actions are either a JSON dictionary specifying an Action, or a list of
Actions.  For instance, the following is a valid Action:

```json
{
  "gpio": {
    "action": "pulse",
    "duration": 0.5,
    "gpio": {
      "function": "buzzer"
    }
  }
}
```

This Action calls the "gpio" action type, and provides it with three
parameters -- a subaction ("pulse", which turns a GPIO on for `duration`
time, and then turns it back off), a duration, and a GPIO specification.  In
this case, the GPIO specification causes the `pulse` to match all GPIOs on
the system that have a `function` of `buzzer`.

The following is also a valid Action:

```json
{ "delay": 0.5 }
```

This Action simply waits for 0.5 seconds before proceeding.  If you executed
this Action on its own, you would see nothing, but if you created a list of
Actions with this as a part of it, you would see a delay happen in between
beeps:

```json
[
  {"gpio": {"action": "pulse", "duration": 0.5, "gpio": {"function": "buzzer"}}},
  {"delay": 0.5},
  {"gpio": {"action": "pulse", "duration": 0.5, "gpio": {"function": "buzzer"}}}
]
```

Another useful type of action is to submit G-code to the MC.  For instance,
you might consider:

```json
{"gcode": "G91\nG0 Z-7.5"}
```

which puts the printer into relative mode, and then jogs the Z axis.

### Testing Actions from the command line

You can use the `x1plus action` command to submit an Action from the command
line.  Like `settings`, it allows you to use JSON on the command line, JSON
from a file, or YAML from a file.  For instance, to make a pleasing
bee-beep! sound from any buzzers that you have connected, consider:

```
# x1plus action --json '[{"gpio": {"action": "pulse", "duration": 0.08, "gpio": {"function": "buzzer"}}}, {"delay": 0.08}, {"gpio": {"action": "pulse", "duration": 0.05, "gpio": {"function": "buzzer"}}}]'
```

You may find it more friendly to edit your actions in JSON on disk.  For
instance, you might prefer:

```
# cat > beep.json <<EOF
[
    {
        "gpio": {
            "action": "pulse",
            "duration": 0.08,
            "gpio": {
                "function": "buzzer"
            }
        }
    },
    {
        "delay": 0.08
    },
    {
        "gpio": {
            "action": "pulse",
            "duration": 0.05,
            "gpio": {
                "function": "buzzer"
            }
        }
    }
]
EOF
# x1plus action --json --file beep.json
```

Or you may even prefer to edit your actions in YAML, since after all, JSON
is a rather unpleasant language to write by hand.  For this, you might
prefer:

```
# cat > beep.yaml <<EOF
- gpio:
    action: pulse
    duration: 0.08
    gpio: 
      function: buzzer
- delay: 0.08
- gpio:
    action: pulse
    duration: 0.05
    gpio: 
      function: buzzer
EOF
# x1plus action --yaml --file beep.yaml
```

If you have an X1P-007 shutter release connected, you might otherwise prefer
to trigger a shutter to test it.  Connect your camera, and try:

```
# x1plus action --json '{"gpio": {"action": "pulse", "duration": 0.15, "gpio": {"function": "shutter"}}}'
```

You can match on other properties, as well.  For instance, if you'd like to
trigger only one of the two connected cameras, and you care about which port
it's on:

```
# x1plus action --json '{"gpio": {"action": "pulse", "duration": 0.15, "gpio": {"function": "shutter", "pin": 3, "port": "b"}}}'
```

This matches on only things that have a function of "shutter", *and* are on
pin 3, *and* are plugged into port B.

### Embedding Actions in G-code

*This section describes in detail how G-code embedded Actions work, but if
you would just like some recipes that you can paste into the G-code window
in your slicer, see below.*

You can run X1Plus Actions from inside G-code.  The general concept is that
you define an action number using a specially-formatted `;x1plus define`
comment, and then use the G-code command `M976 S99 Pn` to trigger it.  For
instance, you can trigger the buzzer with a G-code command sequence as
follows:

```
G0 X... Y...
;x1plus define 5 {"gpio": {"action": "pulse", "duration": 0.2, "gpio": {"function": "buzzer"}}}
M976 S99 P5
G0 X... Y...
```

(Note that an `;x1plus define` must always come before its respective `M976
S99`, and you should not redefine an action number to a new value later in a
print -- however, it is safe to redefine an action to the same value as it had
previously, however.)

#### Using compiled Actions in G-code

Unfortunately, most slicers will not accept commands with `{curly braces}`
-- they seem to interpret these as variable substitution.  X1Plus supports
an alternate "compiled" syntax, which does not include curly braces; you can
use the `x1plus convert` command to convert JSON or YAML into the "compiled"
form.  For instance, you can convert the above action as:

```
# x1plus convert '{"gpio": {"action": "pulse", "duration": 0.2, "gpio": {"function": "buzzer"}}}'
eNqrVkovyMxXslKoVkpMLsnMzwMylQpKc4pTlXQUlFJKixKhggZ6RkABuOK00jy48qTSqqrUIqXa2loAyekZIg==
```

Or, equivalently:

```
# cat > beep.yaml <<EOF
gpio:
  action: pulse
  duration: 0.2
  gpio:
    function: buzzer
EOF
# x1plus convert --file beep.yaml
eNqrVkovyMxXslKoVkpMLsnMzwMylQpKc4pTlXQUlFJKixKhggZ6RkABuOK00jy48qTSqqrUIqXa2loAyekZIg==
```

You can use this "compiled" string the same way as you would a JSON string. 
For instance, to beep on each layer change, you could insert the following
into your layer change G-code in your slicer:

```
;x1plus define 1 eNqrVkovyMxXslKoVkpMLsnMzwMylQpKc4pTlXQUlFJKixKhggZ6RkABuOK00jy48qTSqqrUIqXa2loAyekZIg==
M976 S99 P1
```

You can also use `x1plus convert` to produce readable JSON or YAML from
compiled Actions:

```
# x1plus convert --to=json eNqrVkovyMxXslKoVkpMLsnMzwMylQpKc4pTlXQUlFJKixKhggZ6RkABuOK00jy48qTSqqrUIqXa2loAyekZIg==
{
    "gpio": {
        "action": "pulse",
        "duration": 0.2,
        "gpio": {
            "function": "buzzer"
        }
    }
}
```

#### Pausing G-code until an Action completes

By default, `M976 S99`-triggered Actions will run in parallel with G-code --
i.e., movement commands will continue to run while the Action runs.  For
certain actions -- like time lapses, or waiting for external GPIOs, you may
wish to have G-code wait until an Action completes.  You can do this using
the `M400 W1` and `M400 W0` G-code commands.  `M400 W1` will cause G-code to
stop executing until an Action sends a `M400 G0` G-code.  For example,
consider the following G-code sequence:

```
G0 X100 Y175  ; move the toolhead
G0 X100 Y100
M400          ; wait for all toolhead motion to complete
; Define an action that pulses the shutter, waits, and then resumes G-code execution.
;x1plus define 1 [{"gpio": {"action": "pulse", "duration": 0.5, "gpio": { "function": "shutter" }}}, {"delay": 1.0}, {"gcode": "M400 W0"}]
M976 S99 P1   ; trigger the action
M400 W1       ; pause until the M400 W0 is sent
G0 X175 Y100  ; move the toolhead
G0 X175 Y175
```

This sequence, as described, causes the printer to stop moving until the
Action finishes and the camera has taken its photo (as one might hope for a
potentially long exposure required for good depth of field!).

#### Recipe: triggering a shutter on layer change

The above G-code is appropriate for triggering a shutter, but is not
suitable for embedding in a slicer configuration -- the Action is not
encoded in compiled format.  To use an Action to trigger a shutter, modify
the Machine G-code in your slicer, and add the following to the Layer change
G-code:

```
M400
; pulse shutter for 0.5 seconds, and then wait 1.0 seconds before proceeding
;x1plus define 100 eNqLrlZKL8jMV7JSqFZKTC7JzM8DMpUKSnOKU5V0FJRSSosSoYIGeqZAAbjitNI8uPLijNKSktQipdraWh2gVEpqTmIlUNxQzwDMT0/OT0kFqfM1MTBQCDdQqo0FAMvxJHo=
M976 S99 P100
M400 W1
```

Place these commands immediately underneath the `M971 S11 C10 O0` command. 
(This command will appear twice: one for "without wipe tower", and one for
"with wipe tower".  Insert the commands underneath both.

To start off with, I suggest the following (he says, as a checklist for
himself...):

* Make sure your camera has auto white balance turned off; that your camera
  is set for a fixed ISO, shutter speed, and aperture; and that your camera
  will not attempt to autofocus.
* Home the bed before printing, and then move the toolhead out of the way,
  move the bed up, and focus on or slightly beyond the bed.
* If using a macro / zoom lens, you probably want to stop the aperture down
  more than you think to achieve a usably wide depth of field.
* You probably do not want to shoot 800 RAW photos, so if you normally shoot
  RAW, remember to set the camera to JPEG only...
* Unsurprisingly, smaller layer heights result in "smoother" time lapses.
* The object will grow taller than you think.  If you are zoomed way in,
  consider putting the build area for your part in the very top of the
  frame.
* Don't be afraid to take long exposures!
* If it's an option on your camera, remember to connect it to external
  power (or use a battery emulator, if you're on a camera that has the
  shutter release occupy the same plug as a power adapter).
* Make sure your camera has auto-sleep turned off, if applicable.
* Give your test image one last pixel-peep to make sure you aren't about to
  take a 12 hour time lapse of crap...

#### Recipe: sounding the buzzer

You may also wish to sound the buzzer, either at the end of a print, or upon
a certain layer being reached.  You can paste the following G-code into a
slicer to sound the buzzer for half a second:

```
; sound buzzer for 0.5 seconds
;x1plus define 101 eNqrVkovyMxXslKoVkpMLsnMzwMylQpKc4pTlXQUlFJKixKhggZ6pkABuOK00jy48qTSqqrUIqXa2loAylIZJQ==
M976 S99 P101
```

### Triggering Actions from buttons
