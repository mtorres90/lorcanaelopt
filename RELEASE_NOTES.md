# Release notes

## 2026-09-22 (second release): Achievements

### New

- **Achievements on each player page.** 24 achievements, most with levels, from playing at several stores to win
  streaks, peak Elo, undefeated events, player of the week and Most improved. Earned ones show the date and the
  next level's progress; the rest are listed under "Locked". Rarity (Common to Legendary) is worked out from how
  many players have each level, using the ink colours already in the design. See the README for the full list.
- The About page has a short section on achievements.

## 2026-09-22: Player of the week and seasons

### New

- **Player of the week page.** The player who gained the most Elo each week (Monday to Sunday, at least 4 matches
  and a positive gain) gets the title. The page shows last week's winner, this week's leader so far, a top 10 of
  players with the most titles, and the full log of past weeks.
- **Most improved player per season.** Seasons follow set releases (Set 9 on 2025-09-05 through Set 14 on
  2026-10-23, listed in `seasons.txt`). When the next set comes out the season closes and the player who gained the
  most Elo over it (at least 15 matches and 3 events) gets the prize; the current season shows who is leading.
- The About page has a short section on the awards.

### Changed

- **All paragraph text now spans the full width of the tables** (page introductions, notes, error messages),
  instead of stopping at a narrower column. The About page and footer already did.

## 2026-09-21 (third release): Cleaner player list

### Changed

- **Only players with at least 2 events in Portugal count.** Visitors who played a single tournament here (for
  example a foreign player at one regional) no longer appear, and their matches no longer affect anyone's Elo.
  Set with `--min-events` (default 2; `1` turns it off).
- **`Inkado` and `Crown of Ink Online` events are excluded** from everything (17 events). They are matched by event
  name, so the store that hosts them (which also runs normal events) is unaffected. The list is
  `excluded_events.txt`.
- **Accounts with the same nickname are merged automatically**, keeping the one with the most recent tournament. On the current data this joins 6 players (Brudah, Diogo Santos, Filipe Estrada, Pedro, RichardBlackEye, Tadashi). Accounts that ever played the same event stay separate (one person can't enter an event twice), and so do abbreviated Play Hub names like `Pedro R` and `João M`, which many people share. When the page is built it lists what was merged and what was left apart. `player_merges.txt` merges other accounts by hand, or blocks a merge with `keep <id>`.
- Ratings shift a little because of the above (on the current data, about 11% fewer matches are counted, 5,850 down to 5,232).

## 2026-09-21 (second release): International Elo

### Changed

- **Everyone now starts at 1500** instead of 1000, the same baseline as elorcana.com, so the two ratings are on
  the same scale. Every rating shifts up by exactly 500 and the ranking order does not change.
  (This supersedes the "Elo calculations unchanged" note on 2026-09-21 below.)

### New

- **International Elo on player pages.** Where a player has one, their page shows the Elo from elorcana.com,
  as a number linked to their elorcana profile.
- **International page.** A new menu item ranks the Portuguese players by international Elo, with their elorcana
  rank and their Portugal Elo alongside.
- Only Ravensburger Play Hub profiles are used; Melee profiles (which often duplicate the same person) are ignored.
  elorcana only tracks official events and community events over 512 players, so many local players have none.
  Players are matched by Play Hub name and skipped if that name is shared by several Play Hub players.
  `elorcana_overrides.txt` fixes or hides individual matches.
- The nightly workflow gets a new step, `fetch_elorcana.py`. If elorcana is unreachable the site still publishes.

### Fixed

- The header menu wraps on narrow phones instead of overflowing, now that it has five items.

## 2026-09-21

Site-only changes. Elo calculations, the data pipeline and the nightly workflow are unchanged.

### New

- **Portuguese and English.** Two flags in the header switch the whole site between Portuguese and English:
  menu, page titles, table headings, pagination, stats, chart months, the About page and the footer.
  The site opens in **Portuguese**; the flag a visitor picks is remembered in their browser and used on the
  next visit. Event, store and player names are shown as they come from the Play Hub.
- **Pagination.** Every table (ranking, events, and each player's head-to-head, events and matches) shows
  25 rows per page with Previous/Next controls. Search on the ranking page works together with the paging.
- **Months on the Elo chart.** The player chart now has a time axis with a label at the start of each month
  (and the year on the first month and each January), so progression can be read over time.

- **Hover values on the Elo chart.** Hover (or tap, on a phone) anywhere on a player's chart to see the Elo at
  that point, the date, the result and change, and the opponent. With the keyboard, focus the chart and use
  the left/right arrow keys (Home/End jump to the start/latest, Esc closes).

### Fixed

- **Events table cut off the Matches column.** Long event and store names pushed the last column out of view.
  Names now wrap, so all columns fit; on phones the Store and Players columns are hidden to leave room.
- **Player chart showed values above the player's peak.** The top axis label was the peak plus padding
  (e.g. 1041 for a peak of 1021). The axis now labels the real peak and low. The data itself was correct.
- **Ranking on narrow screens.** Long player names wrap instead of forcing horizontal scrolling.
- **Portuguese About page before a contact is set.** The privacy paragraph read "contacta o contacto do site";
  it now reads "contacta quem gere o site (contacto por definir)". Setting `CONTACT_EMAIL` replaces it with the address.

### Changed

- The About page text and the footer now use the full page width, in line with the tables, on every page.
- The README is now in English.
- Head-to-head tag renamed: "favorite victim" is now **"favorable opponent"** in English and
  **"oponente favorável"** in Portuguese (previously "vítima favorita").
- The chart's horizontal axis is time-based instead of one step per match.

### Notes

- After this is pushed, run **Actions → "Atualizar ranking" → Run workflow** (or wait for the nightly run) to
  publish it to GitHub Pages.
- The older multi-page builder (`build_site.py`) was not updated; the nightly workflow only uses `build_web.py`.
