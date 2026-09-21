# Release notes

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
- The chart's horizontal axis is time-based instead of one step per match.

### Notes

- After this is pushed, run **Actions → "Atualizar ranking" → Run workflow** (or wait for the nightly run) to
  publish it to GitHub Pages.
- The older multi-page builder (`build_site.py`) was not updated; the nightly workflow only uses `build_web.py`.
