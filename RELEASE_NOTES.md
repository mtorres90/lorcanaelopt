# Release notes

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
