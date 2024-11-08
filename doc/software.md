# Getting started with X1Plus Expander

This assumes that you have already [assembled the hardware](assembly.md).

## Installing a firmware

You will need to install an X1Plus firmware build that supports X1Plus
Expander.  Until a release happens that supports X1Plus Expander, this means
that you will need to install a prerelease build.

The currently recommended build is
[f576494](https://nightly.link/X1Plus/X1Plus/actions/runs/11537922100/x1p.zip). 
Download this and unzip the `x1p.zip`; it will contain a file named
similarly to `2.0-19+gf576494.x1p`.  Put this in the root of your SD card,
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
Expander B01.  All four ports will be usable in X1Plus Expander revision C.)
The leftmost port (port B, on revision B01) is always shared with the STEMMA
I2C connector.

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

By default, the shutter release module will short only tip to sleeve.  Some
cameras (notably, Sony cameras) require both tip and ring to be shorted to
sleeve.  To enable this, apply a small amount of solder to bridge each of
the solder jumpers on the back.  Future versions of the X1P-006 board will
come with these pre-shorted (disconnectable using a hobby knife).

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

### Triggering Actions from buttons
