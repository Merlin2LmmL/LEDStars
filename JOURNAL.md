---
title: "LEDStar"
github: "https://github.com/Merlin2LmmL/LEDStars"
description: "A Snowflake shaped Board with 5 arms and one set of red, yellow, white, blue and green LEDs per arm to hang on your Christmas tree!"
created_at: "2026-11-17"
total_time: "18h 30m"
---

# November 17, 2026: Getting the Idea
<!-- fabricate:entry 3341 -->

Well I need a Christmas gift for all of my family members. I thought i should do something personal, creative and show off some of the skills ive learned in the last months... So i decided on gifting them a hardware project and it obviously had to be Christmas related so what better thing to build than a Star that hangs on the branches of your Christmas tree that blinks in programmable patterns!

I then began looking around some existing implementations of this idea and found one kit with some very basic LEDs. I found the color wasnt so nice but i remembered i could change that easily for a little extra price at jlc.
![](https://fabricate.hackclub-assets.com/acb38e513676ba43ec170552009d8fce209c29c8444e70a4cd7418fe61a4c4ca/image-png/image.png)

**Total time spent: 1h**

# November 17, 2026 (entry 2): Deciding what the star has to be
<!-- fabricate:entry 3344 -->

Before drawing anything I wrote down what the star needs to do, because the whole thing has to be cheap: around 10 stars, under 20 € on top of the parts, and ordered together with another JLCPCB order so the shipping is shared.

- **Battery:** a CR2032 coin cell, because AA cells are way too bulky for something hanging on a branch. A coin cell holds about 220 mAh. If the LEDs only get short pulses, one cell should last a whole Advent season.
- **No recharging:** a charger chip, a USB port and a LIR2032 cell would be more parts and more fees. A replaceable cell is fine for a gift.
- **No through-hole parts if possible:** anything THT has to be ordered separately or hand-soldered, and that costs shipping. The battery holder is the only thing I accept.
- **Programming without a connector:** just bare pads and my ESP32-S3 dev board as a USB-serial adapter. The 1 k resistor for the one-wire line sits on the board, so I only need jumper wires.
- **No addressable LEDs:** I first wanted WS2812-style RGB LEDs, but they want 3.5 V or more. They also draw about 1 mA each even when "off", so 8 of them would empty a coin cell in days. Plain single-colour LEDs, multiplexed by the chip, it is.
- **LED colours:** red, green, blue and white. White and blue only just work at 3 V, and they drop out first when the cell gets weak. That is why every colour gets its own resistor value.
- **Programmable:** I decided i wanted to later add different color patterns in different colors and maybe even different modes for it. So programming is a must have.

I picked the **ATtiny404** (SOIC-14, UPDI programming), and I drew the whole schematic around it, with a piezo buzzer for a few bars of Silent Night.
![](https://fabricate.hackclub-assets.com/076cef58fc78c92572be594e984a9ca90e41b09f4b5f79b98233df2781ac3169/image-jpeg/02_attiny_plan.jpg)

**Total time spent: 2h**

# November 17, 2026 (entry 3): Reconsidering my life choises
<!-- fabricate:entry 3345 -->

Next I checked every part against JLCPCB's catalogue to see what is Basic (no extra fee) and what is Extended (about 3 $ per line). The good news: resistors, the 100 nF capacitor and the white, red and green LEDs are all Basic. The bad news: every microcontroller is Extended, and the real problem was the price. The ATtiny404 costs around 1.25 to 1.50 $ each and only 132 were in stock. With the fees, the whole batch came to roughly 45 $, way above my 20 € target.

So I looked at the alternative from my first idea list, the **WCH CH32V003F4P6**:

| | ATtiny404 (SOIC-14) | CH32V003F4P6 (TSSOP-20) |
|---|---|---|
| Price | about 1.25–1.50 $ | about 0.29 $ |
| Stock at LCSC | 132 | over 7000 |
| Flash / RAM | 4 KB / 256 B | 16 KB / 2 KB |
| Pins | 14 | 20 (enough for the whole LED matrix) |
| Programming | UPDI, my ESP32 would work | one-wire SWIO, needs a WCH-LinkE (about 7 €) |

(I hope this table gets rendered correctly)

I also dropped the buzzer (a THT part that adds a fee and eats battery), kept the blue LED and added a yellow LED.

Then I rebuilt the schematic: 5 arms with 5 colours each, 25 LEDs in total. One resistor per colour, so every colour can be tuned separately. The LEDs are multiplexed: the chip switches on one arm at a time and cycles through them quickly. The programming pads are now just GND, 3V3 and SWIO. There is no resistor for the programmer anymore.

![](https://fabricate.hackclub-assets.com/2104430c9b998dc489a6bc8c980995fb8e22251b7dfcf0a330a53dd5625efe58/image-png/image.png)

**Total time spent: 3h**

# November 17, 2026 (entry 4): Deciding on the PCB Outline and LED ordering
<!-- fabricate:entry 3347 -->

With the schematic done I moved on to the board. The first outline was a plain 5-pointed star. I let a script draw the outline, because my own attempts were never perfectly symmetric. I also made a second version with sharper angles between the arms ("classic") next to the "chunky" one in the picture.

I arranged the colors, from the centre of the arm to the tip: red, yellow, white, blue, green. My reasoning:

- White is in the middle because it is the main colour and carries the brightness.
- Yellow and blue sit right next to white, so I can tune the white temperature later by mixing them in.
- Red and green are the most saturated, they sit further out, and they work fine on their own.

This time i learned my lesson and first did the netclasses so that itd be easier to route later on even tho it didnt turn out to be much of a time saver in the end...

Here are the star outlines:
"chunky":
![](https://fabricate.hackclub-assets.com/3612a981eef40dc585b83345a1f942f9de12d1c9e2c312056b660b2a50967676/image-png/04_star_outline.png)
"classic":
![](https://fabricate.hackclub-assets.com/fda65b8e214e83c1b6f241849a6991cd32bf9e3c53f2097146f20999e6ddb7a5/image-png/image.png)

**Total time spent: 1h 30m**

# November 17, 2026 (entry 5): Routing the first version
<!-- fabricate:entry 3348 -->

Now i simply placed the components on the board (all LEDs on the end of the arms) and the test inside the middle with the cap close to the vin pin for noise reduction. Then i went on to routing the PCB. That was pretty straight forward and probably the most relaxing thing on the journey looking back at it (yes i am writing all those journals afterwards beacause I was too lazy writing them all immediately. Here is a look at the finished Routing:
![](https://fabricate.hackclub-assets.com/2409d569f6e1439ec9ced5f7232dfdd3cd4ea3a9287a11363ce519b0e001a409/image-png/image.png)

**Total time spent: 48m**

# November 17, 2026 (entry 6): Letting the LEDs shine through the board
<!-- fabricate:entry 3349 -->

I had two problems with the first design. The battery and all the parts are on the same side as the LEDs, which looks bulky. And JLCPCB's cheap assembly only places parts on one side, so I could not just move the battery to the back.

My idea: what if the LEDs shine **through** the board? I got the idea from the "extension shield adapter by Eduart, a Robotics company we have gotten the boards for our two robots from. That board used reverse-mount LEDs where the lens points at the PCB. You cut a hole in the board under each LED and the light comes out the back. The front, with the battery and chip, would then be the back of the ornament.

I searched the JLCPCB catalogue for those. That was really a headache to do because i find lcsc very hard to search in so it took me way too long for me to want to admit. In 0603 and 0805 I found none. In **1206**, the XINGLIGHT XL-3216 series exists in all five colours, and every colour is in stock at roughly 1 to 2 cents each. They are all Extended parts, so there are five more fees, but I think the look is worth it.

What changed:
- New footprint for the XL-3216 with a 1.4 mm round hole under every LED. The red LED has its pins the other way around, so it needed its own footprint variant.
- All 25 LEDs in the schematic switched to the new parts. ERC had 0 errors.
- I rerouted the board. Thanks to the generous clearance i (obviously purposely duh!) added it was quick, and I got 0 DRC errors.

I also dropped the programming header. The jumper wires are going straight into three bare pads, because the programmer exposes single pins anyway, and a header would only end up in the BOM for nothing.

![](https://fabricate.hackclub-assets.com/4d4a990a8c3cd83ad0f5bd13ff95fa4e0a89b7363b62ee58bc8085409b3c959b/image-png/05_backlit_pcb.png)

**Total time spent: 2h 30m**

# November 17, 2026 (entry 7): Reconsidering my life choises ... part 2
<!-- fabricate:entry 3350 -->

With the electronics sorted I wanted the outline to look special, so I decided it should be a **snowflake**. This turned out to be the hardest part of the whole project. I tried out a lot of versions but it never quite looked right and keeping it symmetric by hand was quite hard:

1. Thin arms with bar-shaped branches. Looked brittle and the branches looked like blocks glued on.
2. Thicker arms with round-ended branches. Sturdier, but it looked like an oak leaf or an acorn.
3. Too many spikes. They overlapped and you could not recognize a snowflake anymore.
4. Finally I downloaded a picture of a snowflake I liked, put it in kicad and traced the boards outline over it.

After a few more rounds (the arms looked too thin, the branches too blocky) the outline finally worked. I rerouted all 25 LEDs along the new thin arms with little space and the LED pads at least 2 mm from the edge.

![](https://fabricate.hackclub-assets.com/b30da452f41626bb2f8e27eedb03493099fd79065d3d434a6011ed9ac8a15f06/image-png/06_snowflake_pcb.png)

**Total time spent: 2h**

# November 17, 2026 (entry 8): Back silkscreen, the repo and JLCPCB being a pain in the ass
<!-- fabricate:entry 3351 -->

The back side has hardly any traces, so it can carry decoration. I added a pattern on the back silkscreen. Later I redid it as a cleaner design that follows the shape of the board: one line inside the outline, a small nested V inside each of the 20 points, and two stars in the middle with ridges. It is centred on the true middle of the board and drawn at JLCPCB's minimum line width of 0.15 mm.

I also put everything on GitHub with the CERN-OHL-S-2.0 license and wrote the README so that the thinking process, including the first ATtiny404 idea, stays visible.

Then I hit a problem: in JLCPCB's quote tool the **Economic** assembly option was greyed out. I tried making the outline a rectangle with break-off tabs, but that did not help. The message said the board specs are not supported for Economic PCBA. I reverted the tabs and decided to assemble them myself: I would order the PCBs with a stencil and the parts from LCSC. The expensive parts are the one-time tools (hot plate, soldering gear), and I will use them for other boards later too. The only thing is: I will need such a hotplate lol... I read that you guys could arrange something, where you send a soldering iron for a project beforehand... Maybe the same thing works for a hot plate? I already got a soldering iron.

While I was researching the LEDs, I found out they are quite sensitive. The XINGLIGHT datasheets say about 300 °C and a maximum of 3 seconds per pad with an iron, and I should only solder each pad once. So I will not heat from the back (hot air would hit the lens through the window as i found out).

![](https://fabricate.hackclub-assets.com/d69b60b9d2c477d5005b15ff7dce77b89e1eac4377c81603fb6de34ab2f4d67a/image-png/07_back_silkscreen.png)

**Total time spent: 1h 12m**

# November 17, 2026 (entry 9): Doing some heavy blender rendering
<!-- fabricate:entry 3352 -->

Since the LEDs shine through the board, I wanted to see how the ornament would look on a real tree before ordering. I built a scene in Blender (Cycles, GPU rendering on my AMD RX 9070 XT desktop). The ornament is not posed by hand:

- The board is a rigid body with real gravity.
- The red string is a chain of small rigid links that runs through the hang hole and over a real twig of the tree (a CC0 Poly Haven fir model).
- The board starts too high and tilted, and the physics simulation lets it drop and swing until it hangs still.

It took many tries before it looked right. The string end stuck out into the air and for a while the camera showed the front of the board instead of the back. In the end I found a spot between the branches with a bit of background and some baubles. I also gave the board a glossy white solder mask, like the ones I will order, and made the silkscreen matte black.

For the README gallery I render three LED colour sets (white + yellow, white + blue, red + green) from three camera angles each. Every image is 2400 × 1600 pixels at 512 samples and takes about 3 minutes. I even found a bauble that was clipping into the tree and fixed the placement script before the final batch.

![](https://fabricate.hackclub-assets.com/7f20acae314c9249a36466117c58281e70dc222c22796e91e0213fec73bf882e/image-jpeg/08_render.jpg)

**Total time spent: 3h 30m**

# November 18, 2026: Added 3 pos switch and mode switch
<!-- fabricate:entry 3361 -->

I am so dumb lol. How did i forget to add buttons for changing modes lol. I literally mentioned it in the first or second journal. How else are you supposed to switch between on, off and clock mode. Now you do that with a 3 positional switch. And I mentioned wanting to program different light patterns. For that i added a separate switch. It was a quick fix for the schematic: Just one Button + a pull down resistor and one 3 positional switch + diode + another resistor. When i annotated i clicked on "replace all annotations" which messed up all labels of the existing pcb so that was an experience relabeling all of them. I decided to put the 3 positional switch on the edge of the board on top and the mode switch where ever there was space.

![](https://fabricate.hackclub-assets.com/ec9ac4acf868168f18ceffcef62e969139aa95679e021b33f0a018e6da77074c/image-png/image.png)
![](https://fabricate.hackclub-assets.com/eb54e2659c60139ac29d08b9389d324eef50ef89d129cf53d7d9ee5356be659f/image-png/image.png)

**Total time spent: 1h**
