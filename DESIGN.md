# How this page is made

The profile is a set of "plates": SVG images drawn by Python scripts, in the manner of a Swiss poster series. One mascot, a koi, appears in several of them. The scripts are kept in a private repository; what is here is their output.

## The idea

A koi seen from above is a spine with a width. Give the spine a travelling wave and the fish swims; put a grid over it and it is pixel art; sample it and it is a scatter plot. So the same geometry is drawn swimming on the Wave button, nine different ways in Koi-studies, and as a live simulation on the pond page.

## Palette

| Token | Light | Dark | Used for |
| --- | --- | --- | --- |
| paper | `#F4F2ED` | `#181716` | the sheet every plate sits on |
| ink | `#141413` | `#F3EEE5` | titles and values |
| soft | `#69645C` | `#A59E92` | labels and captions |
| line | `#F0B3A1` | `#6A443A` | the hairline grid |
| blue | `#2A20D2` | `#3329E0` | water, panels, the primary action |
| red | `#EC2A2D` | `#FF4D40` | markings, the one accent |
| cream | `#F8EDD9` | same | the koi, and line work on blue |

Every plate carries both themes in one file: its colours flip with the reader's light or dark setting. Each work tile is drawn in the colour its project already uses, and tests hold line art and numbers to a contrast of 4.5 to 1 or better in both themes.

## The opening

The first plate is the first sentence of the profile, shown the way an entity recogniser reads it: the name in a dashed box, six phrases highlighted, each with a label and a score. A tilted print-out repeats the sentence de-identified, with every entity under a bar. The scores are part of the drawing; no model was run on the sentence. Each label wears the colour of one work tile, so the plate doubles as a legend for the tiles below it.

## The pond's cast

Each koi has a name, a variety and a seed, and it hatches when the visit count reaches its number. The seed fixes a koi's markings for good, and the markings grow as the koi ages.

| Koi | Variety | Hatches at |
| --- | --- | --- |
| Epoch | kohaku: cream with red steps along the back | the start |
| Dropout | sanke: a kohaku with small black spots | the start |
| Overfit | ogon: one gold, lighter along the back | the start |
| Bias | tancho: cream with one round red crown | 100 visits |

Three more animals share the water: ReLU the frog, Jitter the dragonfly and Outlier the kingfisher. Where everything is at a given moment follows from what the pond knows right then: the counts, the weather, the last clicks and the time.

- Feeding puts pellets on the water for 45 seconds and the nearest koi turn to eat. Waving makes the frog lift an arm, and rings spread from its pad.
- The kingfisher visits twice a day for 20 minutes. While it is there the koi keep their distance.
- Rain draws rings and wind draws ripples. The dragonfly is out in the light theme and fireflies in the dark one.
- A lotus opens for every two weeks of the commit streak, three at most.

## The live pond

The pond on the profile is not a file. Each view asks a small function of my own for the picture, and the function draws it fresh: the cast at that moment, the counts of visits, pellets and waves, how many of the day's pellets are gone, and Melbourne's time and weather.

- Feed and Wave in the README are links to the function. A person's click is counted and the visitor goes straight back to the pond on the profile. Prefetches, link previews and machines that say what they are go back without being counted.
- The koi share 30 pellets a Melbourne day; after that they are full.
- The function stores and logs nothing about a visitor; Vercel, which hosts it, keeps its own request logs, as any web host does. The store holds counts and times, nothing else.
- The weather comes from Open-Meteo. Only a look (clear, cloud, rain or wind) and a whole temperature are kept.
- Every failure ends in a picture: if the store or the weather cannot be reached, the pond is drawn from last night's numbers.
- Each night a job reads the counts back into the record kept here, and never lowers one.

## Type

TeX Gyre Heros (a Helvetica) for titles and labels, Fragment Mono for captions. Titles are bold, tight and large; captions are small, grey and written like prompts. Type on the plates is outlined to paths, because README images cannot load fonts.

## Grid

Plates are 840 wide with a 20 margin, four columns of 188 and 16 gutters. A plate reads top to bottom: a title cell two columns wide, two small fact cells, the artwork laid over empty cells at a slight angle, then a "Prompt" cell and its caption.

Every big plate has a phone-width twin that is re-set, not shrunk: the type stays readable and the artwork is re-composed.

## Motion

- Everything moves a little; nothing moves a lot. Loops are slow and each one means something: a recogniser tagging a sentence again, a forecast interval breathing, a progress bar that will not finish.
- The first frame is always a complete picture, because some viewers freeze animation.
- A reader who asks for reduced motion gets still plates, and the pond page's Motion switch starts off for them.

## House rules

- Copy is plain and first person.
- Every image has alt text that says what a sighted reader gets from it.
- Numbers on the page are real and sourced; WardSignal is always described as a prototype on synthetic data.
- Nothing asks a visitor to log in.
