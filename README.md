# The World in One Image — 20 November 2026

[![make.fun · news-image-20261120](https://make.fun/badge/news-image-20261120.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![rank](https://make.fun/badge/news-image-20261120/Dadapy04/news-image-20261120-b/rank.svg)](https://make.fun/bounty/news-image-20261120/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![reward](https://make.fun/badge/news-image-20261120/Dadapy04/news-image-20261120-b/reward.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)

## The concept

One day of world news, compressed into a single editorial front page.

The poster does not list the day — it weighs it. The lede story runs full width.
Every other story becomes a band whose width is its exact share of the day's
coverage weight (19/17/16/11/7 of the remaining 70, rendered as a
drift-free proportional bar), so the layout itself argues about what mattered
most on 20 November 2026: a 400-drone strike on Ukraine that spilled into
Polish airspace, Trump's Asia summit and his threat to bar US firms from
building data centres abroad, a NATO-like security guarantee floated for Kyiv,
the Senate refusing to check the Iran war, and coordinated wage protests across
more than 25 European countries.

Every element is drawn from an embedded 5x7 bitmap font — no fonts to install,
no image library to fetch, no network, no model. The same fixture always
produces the same bytes, which is what `--check` proves.

## Run it

```sh
python3 main.py            # writes out/2026-11-20.png
python3 main.py --check    # renders twice, asserts identical bytes
python3 main.py --stats    # story count, total weight, canvas height
```

Pure Python 3 standard library (zlib + struct). No `pip install`, no
dependencies of any kind. Requires Python 3.7+.

## Layout

- `main.py` — the generator: canvas primitives, bitmap font, layout, PNG writer.
- `news.json` — the fixed fixture: 6 stories with weights and sources, plus a wire strip.
- `out/2026-11-20.png` — the rendered poster, 1600x2740.

## License

MIT — see `LICENSE`.
