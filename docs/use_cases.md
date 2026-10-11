# Reservation Page Use Cases

## Happy Path: Reserve a Space

**Goal:** A user books an available space and optionally adds equipment.

**Preconditions:** The system has spaces and equipment available. The selected space and any requested equipment are available for the requested time block.

**Time blocks:** Reservations are made in fixed 2-hour blocks from 10:00 to 22:00 in the lounge's local time: 10:00–12:00, 12:00–14:00, 14:00–16:00, 16:00–18:00, 18:00–20:00, and 20:00–22:00. A block is identified by a date and an hour range. Users cannot choose custom start or end times.

**Errors:** For each error, the system preserves the user's selections, explains the issue, and allows the user to correct it without restarting the booking flow. Error codes in parentheses match `openapi.yaml`.

### 1. Browse the Home Page

1. The user lands on the home page.
2. The system displays the current time block (for example, "Current time block · Sep 23, 2026 · 16:00–18:00"), which spaces are available in it, and reservations currently in progress. Outside lounge hours, it shows the next time block instead.
3. The user reviews the spaces and their details, then opens the reservation page.

**Expected result:** The user can identify a suitable space and begin booking it. Availability in the current block is distinct from availability for a future block.

#### Scenarios

Good:

- **During lounge hours** — The home page shows the block in progress, marks each active space as Available or Reserved for that block, and lists the reservations in progress.
- **Outside lounge hours** — Before 10:00 or after 22:00, the home page shows the next block instead and says the lounge is closed. No reservations are listed as in progress.
- **No reservations in progress** — Every active space shows as Available and the in-progress list is empty.
- **Open space details** — Choosing a space opens its details page, showing its computer specs and a way to reserve it.

Bad:

- **Inactive space** — A space that has been turned off in Settings shows as Inactive and cannot be chosen for booking.
- **Inventory cannot load** — The home page shows an error instead of an empty list, so the user does not think the lounge has no spaces.

### 2. Choose Reservation Details

1. The user selects a space.
2. The user selects a date and then one of that date's time blocks. Blocks that have already started or are booked for the selected space are shown but cannot be selected.
3. The system checks that the block has not started.
4. The system verifies that the space is available for the selected block.
5. The user optionally selects equipment. The system shows which items are available for the selected block.
6. The user proceeds to review the reservation.

**Expected result:** The user has selected a valid space and time block, with or without optional equipment.

#### Scenarios

Good:

- **Pick a free block** — The user picks a space, a date, and a free block that has not started. They can continue to review.
- **Pick a future date** — Choosing another date reloads that date's six blocks with that date's availability.
- **Add equipment** — Only equipment free in the selected block can be selected. Changing the block refreshes the list.
- **Skip equipment** — The user continues without equipment. See the alternate happy path below.
- **Equipment in use now** — An item is in use in the current block. It can still be selected for a different block.

Bad:

- **Block already started** — Blocks that have started are shown but disabled. If one is submitted anyway, booking is blocked. (400 `BLOCK_STARTED`) “Choose a time block that has not started yet.”
- **Block booked for this space** — The block is shown but disabled for the selected space. The user can change the space or the block.
- **Time is not a defined block** — A direct API call names a start hour other than 10, 12, 14, 16, 18, or 20. The request is rejected. The UI only offers defined blocks. (400 `INVALID_TIME_BLOCK`) “Choose one of the available time blocks.”
- **Missing details** — The user tries to continue without a space, date, block, or name. They stay on the page and see which field is missing. (400 `MISSING_FIELD`)

### 3. Review and Confirm

1. The system displays a summary containing the space, date, time block, and any equipment.
2. The system asks, “Are you sure you want to schedule this reservation?”
3. The user can return to edit the details or confirm the booking.
4. The user confirms the reservation.
5. The system rechecks availability and saves the reservation with its selected equipment. The availability check and booking must prevent competing users from booking the same resources in the same block.

**Expected result:** A confirmed reservation is created, and the space and selected equipment are reserved for that block.

#### Scenarios

Good:

- **Confirm** — The summary matches the selections. The user confirms and a reservation is created with status CONFIRMED.
- **Go back and edit** — The user returns to their selections from the review step. Nothing is booked and their selections are kept.
- **Back-to-back blocks** — The same space is booked 14:00–16:00 by one reservation and 16:00–18:00 by another. Both succeed.

Bad:

- **Space booked by someone else** — Another user booked the space for that block after the page loaded. No reservation is created. (409 `SPACE_BOOKED`) “This space is already booked during your selected time. Choose another space or time.”
- **Equipment booked by someone else** — A selected item was booked for that block. No reservation is created, and the user can remove the item, pick another, or change the block. (409 `EQUIPMENT_UNAVAILABLE`) “This equipment is unavailable during your selected time.”
- **Space turned off** — The space was made inactive in Settings before confirmation. (409 `SPACE_INACTIVE`) “This space is not open for reservations. Choose another space.”
- **Several conflicts at once** — The space and equipment both became unavailable. No partial booking is created. (409 `AVAILABILITY_CHANGED`) “Availability changed. Please review your space and equipment selections.”
- **Block started during review** — The block started while the user was on the review step. (400 `BLOCK_STARTED`) “Choose a time block that has not started yet.”
- **Space or equipment removed** — A selected space or item no longer exists. (404 `SPACE_NOT_FOUND` or `EQUIPMENT_NOT_FOUND`)
- **Save fails** — The system cannot save the reservation. No booking is created, and the user can retry without making a duplicate. Success is shown only after the booking is confirmed. (500 `RESERVATION_FAILED`) “We couldn't complete your reservation. Please try again.”

### 4. View Booking Confirmation

1. The system displays a success message and the reservation details.
2. The user can review the confirmed booking.
3. The system updates availability for the booked block. When the block begins, the reservation appears among the ongoing reservations on the home page.

**Success outcome:** The user knows the booking succeeded and can clearly see where and when to arrive and which equipment is included.

#### Scenarios

Good:

- **Confirmation shown** — The success message shows the space, date, block, and equipment (or “No additional equipment”).
- **Availability updated** — The booked space and equipment no longer appear as free for that block to any user.
- **Appears on home page** — When the block begins, the reservation is listed among the reservations in progress.

Bad:

- **No confirmation without a booking** — If the save failed, the success message is never shown. The user sees the error from step 3 instead.

## Alternate Happy Path: Reserve Without Equipment

The user follows the same booking flow but skips equipment selection. The review and confirmation screens show “No additional equipment.” The reservation succeeds as long as the space and time block are valid.

#### Scenarios

Good:

- **No equipment** — The reservation is created with no equipment, and equipment availability is unchanged.

Bad:

- **Space unavailable** — Skipping equipment does not bypass the space checks. The same space and block errors from steps 2 and 3 apply.
