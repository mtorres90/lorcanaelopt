# Elo Lorcana Portugal

Elo ranking of Disney Lorcana players in Portugal, inspired by EloShowdown (Riftbound).

The site is available in Portuguese (default) and English; visitors switch with the flags in the header and the choice is remembered in their browser. See `RELEASE_NOTES.md` for what changed in each release.

## Scope

- Only events at stores in **Portugal**.
- Only the **post-rotation** era: from **2025-09-05**, the release date of Set 9 (Fabled), which started the rotation.
- Only the **Core Constructed** format by default (change it with `--formats`). Draft, sealed and other booster formats do not count towards the Elo.
- Players need at least **2 events in Portugal** to count at all (`--min-events`), which leaves out visitors who played a single tournament here. Their matches are ignored, not just hidden.
- Events listed in `excluded_events.txt` (by name, e.g. `Inkado`, `Crown of Ink Online`) are ignored.
- Play Hub accounts with the **same nickname** are merged into one player, keeping the account with the most recent tournament (a tie goes to the one with more events). Accounts that ever played the same event are kept separate, since one person can't enter an event twice, and so are abbreviated Play Hub names like `Pedro R`, which many people share. `player_merges.txt` merges accounts with different names by hand, or blocks an automatic merge with `keep <id>`. `--no-auto-merge` turns the automatic merge off.

## How it works (everything on GitHub, nothing to run on your computer)

GitHub Actions runs every night: it collects the results from the Ravensburger Play Hub, calculates the Elo and publishes the page to GitHub Pages.

1. Create an account on github.com and a **public** repository (e.g. `lorcana-pt-elo`). Free Pages requires a public repository. Player data is not stored in the repository, only in the published page.
2. Unzip this archive and upload the files: **Add file → Upload files**. Make sure the `.github/workflows/` folder is there with the two `.yml` files. If your system hides dot-folders, create each file with **Add file → Create new file**, typing the full path (`.github/workflows/update.yml`) and pasting the contents.
3. **Settings → Pages → Source: GitHub Actions**.
4. **Actions → "Descobrir a API do Play Hub" (Discover the Play Hub API) → Run workflow.** When it finishes, open the run, copy the text of the "Sondar a API" (Probe the API) step and paste it into the conversation. It is used to confirm the paths and field names of the API before you publish real data.
5. Once adjusted: **Actions → "Atualizar ranking" (Update ranking) → Run workflow.** The page address appears in the "deploy" step.
6. Optional: **Settings → Secrets and variables → Actions → Variables**, create `CONTACT_EMAIL` with the email address for removal requests.

## Integration status

Written from public sources about the API. The "TV" endpoints are confirmed; the paths for events, rounds and matches and the field names are the most likely ones but **have not yet been tested against the real API**. The tests use a mock server, so they prove the mechanics (pagination, filters, cache, CSV) and not the real shape of the data. Step 4 exists to close this gap.

The Play Hub blocks requests from browsers on other sites (CORS), so collection runs on GitHub's servers and the final page only shows data that has already been calculated.

## Files

| File | Purpose |
|---|---|
| `ingest_playhub.py` | Collects Portuguese events, rounds and matches from the Play Hub and writes the CSV. `--probe` shows the shape of the data |
| `import_matches.py` | Imports the CSV into SQLite (idempotent, ignores byes, filters dates) |
| `elo.py` | Elo engine: start at 1500, K=40 for the first 10 matches and K=24 after that, draw = 0.5, rounds calculated with the rating from before the round |
| `fetch_elorcana.py` | Fetches each player's international Elo from elorcana.com (Play Hub profiles only, matched by nickname) and caches it in `raw/elorcana.json` |
| `curate.py` | Rules applied before the Elo is calculated: excluded events, merged accounts, minimum events. Used by both the site and the elorcana fetch |
| `excluded_events.txt`, `player_merges.txt` | Edit these to exclude an event by name or merge two accounts. When the site is built it lists names shared by different ids, to help you spot more duplicates |
| `awards.py`, `seasons.txt` | Player of the week and most improved player per season. `seasons.txt` lists the set release dates that start each season; add a line when a new set comes out |
| `build_web.py` | Generates the single page (`index.html`) with ranking, players, events and about |
| `build_site.py` | Alternative: multi-page site |
| `make_sample_data.py` | Made-up data for trying things out |
| `.github/workflows/` | `probe.yml` (discovery) and `update.yml` (nightly update and publishing) |

## Player of the week and seasons

The **Player of the week** page shows, from the same curated matches as the ranking:

- **Weekly title:** the player who gained the most Elo in a week (Monday to Sunday), with at least 4 matches that week and a positive gain (`--potw-min-matches`). Ties go to more matches, then higher Elo. The week in progress is shown as "so far" and only counts once it has ended.
- **Top 10** by number of weekly titles, and the full **weekly log**.
- **Most improved player of each season:** a season starts on a set's release date (`seasons.txt`) and ends when the next set is released, which is when the prize is awarded. Improvement is the Elo gained across the season, with at least 15 matches and 3 events in it (`--season-min-matches`, `--season-min-events`). The current season shows who is leading so far.

## International Elo (elorcana.com)

Each player page shows the player's international Elo from [elorcana.com](https://elorcana.com), linked to their profile there, and the **International** page ranks the Portuguese players by it.

- Only **Ravensburger Play Hub** profiles are used. elorcana also has Melee profiles, and the same person often has one of each, so anything from Melee is ignored.
- elorcana has its own player ids, so players are matched by their Play Hub name. If more than one Play Hub profile has exactly that name the player is skipped, not guessed.
- elorcana only tracks official events and community events with over 512 players, so many local players will not have an international Elo.
- To fix a wrong or missing match, add a line to `elorcana_overrides.txt`: `<play hub id> <elorcana profile uuid>` to force a profile, or `<play hub id> none` to hide it.
- The nightly workflow runs `fetch_elorcana.py` before building the page. If elorcana is unreachable the site is still published, with the previous values.

## CSV format between the collector and the importer

```
event_id,event_name,event_date,store,city,round,player_a_id,player_a_name,player_b_id,player_b_name,result
```

`result` is `A`, `B` or `D` (draw). Without `player_b_id` it is a bye. `player_*_id` must be the player's stable id, not their name.

## Try it locally (optional)

```bash
python make_sample_data.py
python import_matches.py data/sample_matches.csv --db data/demo.db
python build_web.py --db data/demo.db --out web/index.html --demo
python -m unittest
```

## Privacy

The name shown is the Play Hub username; if there is none, first name and initial of the surname, never the full name.
To leave someone out, put the player's id in `opt_out.txt` (one per line): their page disappears and their name becomes "Anonymous player" ("Jogador anónimo" in Portuguese) in their opponents' lists.
