-- Overwatch match scenario. Load after sampledata.sql (scripts/seed.py --dataset overwatch).
-- Books every desk for an Overwatch match in the current time block, or the next
-- block when the lounge is closed, so the overview shows every station reserved.
-- Station 06 is brought back online for the match.

-- The block the overview shows: the one in progress now, or the next one.
-- Blocks start on even hours from 10:00 to 20:00 in the session time zone.
CREATE TEMPORARY TABLE match_block AS
SELECT
  CASE
    WHEN h < 10 THEN TIMESTAMP(CURDATE(), '10:00:00')
    WHEN h >= 22 THEN TIMESTAMP(CURDATE() + INTERVAL 1 DAY, '10:00:00')
    ELSE TIMESTAMP(CURDATE(), MAKETIME(h - (h % 2), 0, 0))
  END AS start_time
FROM (SELECT HOUR(NOW()) AS h) AS clock;

UPDATE Spaces SET is_active = TRUE, description = 'PC gaming desk with a 165Hz monitor.' WHERE space_id = 6;
UPDATE Computers SET status = 'AVAILABLE' WHERE space_id = 6;

-- Free the block: remove regular bookings that would collide with the match.
DELETE FROM ReservationEquipment WHERE reservation_id IN (
  SELECT reservation_id FROM Reservations
  WHERE start_time = (SELECT start_time FROM match_block)
);
DELETE FROM Reservations WHERE start_time = (SELECT start_time FROM match_block);

INSERT INTO Reservations (reservation_id, user_name, space_id, start_time, end_time, status, created_at)
SELECT 9000 + space_id, 'Overwatch Match', space_id, start_time, DATE_ADD(start_time, INTERVAL 2 HOUR),
       'CONFIRMED', DATE_SUB(NOW(), INTERVAL 3 DAY)
FROM Spaces CROSS JOIN match_block
ORDER BY space_id;

-- Headsets for comms on the first two desks; the third headset is in maintenance.
INSERT INTO ReservationEquipment (reservation_id, equipment_id) VALUES
  (9001, 1),
  (9002, 2);

DROP TEMPORARY TABLE match_block;
