-- Demo data for the tables in schema.sql. Run schema.sql first.
-- Reservation times are relative to today in the session time zone, so the
-- demo always shows bookings for today and tomorrow no matter when it is seeded.
-- Every block today has at least one confirmed booking, so the overview always
-- shows a reserved station.
-- Station 06 is inactive; reservation 8805 was booked before it was turned off and is kept.

INSERT INTO Spaces (space_id, space_name, description, is_active) VALUES
  (1, 'Station 01 - Cyberhound Rig', 'PC gaming desk with a 240Hz monitor.', TRUE),
  (2, 'Station 02 - Cyberhound Rig', 'PC gaming desk with a 165Hz monitor.', TRUE),
  (3, 'Station 03 - Cyberhound Rig', 'PC gaming desk with a 240Hz monitor.', TRUE),
  (4, 'Station 04 - Cyberhound Rig', 'PC gaming desk with a 165Hz monitor.', TRUE),
  (5, 'Station 05 - Cyberhound Rig', 'PC gaming desk with a 240Hz monitor.', TRUE),
  (6, 'Station 06 - Cyberhound Rig', 'PC gaming desk with a 165Hz monitor. Out for repairs.', FALSE);

INSERT INTO Computers (computer_id, space_id, hostname, specs, status) VALUES
  (1, 1, 'CH-RIG-01', 'Intel Core i7-13700K, RTX 4080, 32GB DDR5 RAM, 1TB NVMe SSD, 240Hz Monitor', 'AVAILABLE'),
  (2, 2, 'CH-RIG-02', 'AMD Ryzen 7 7800X3D, RTX 4070 Ti, 32GB DDR5 RAM, 2TB NVMe SSD, 165Hz Monitor', 'AVAILABLE'),
  (3, 3, 'CH-RIG-03', 'Intel Core i7-13700K, RTX 4080, 32GB DDR5 RAM, 1TB NVMe SSD, 240Hz Monitor', 'AVAILABLE'),
  (4, 4, 'CH-RIG-04', 'AMD Ryzen 7 7800X3D, RTX 4070 Ti, 32GB DDR5 RAM, 2TB NVMe SSD, 165Hz Monitor', 'AVAILABLE'),
  (5, 5, 'CH-RIG-05', 'Intel Core i7-14700K, RTX 4080 Super, 32GB DDR5 RAM, 2TB NVMe SSD, 240Hz Monitor', 'AVAILABLE'),
  (6, 6, 'CH-RIG-06', 'AMD Ryzen 5 7600X, RTX 4060, 16GB DDR5 RAM, 1TB NVMe SSD, 165Hz Monitor', 'MAINTENANCE');

INSERT INTO Equipment (equipment_id, item_name, category, serial_number, status) VALUES
  (1, 'Logitech G Pro X Wireless Headset #1', 'HEADSET', 'MOCK-HEADSET-001', 'AVAILABLE'),
  (2, 'Logitech G Pro X Wireless Headset #2', 'HEADSET', 'MOCK-HEADSET-002', 'AVAILABLE'),
  (3, 'Xbox Elite Wireless Controller #1', 'CONTROLLER', 'MOCK-CONTROLLER-001', 'AVAILABLE'),
  (4, 'DualSense Wireless Controller #1', 'CONTROLLER', 'MOCK-CONTROLLER-002', 'AVAILABLE'),
  (5, 'HyperX Cloud II Headset #3', 'HEADSET', 'MOCK-HEADSET-003', 'MAINTENANCE');

INSERT INTO Reservations (reservation_id, user_name, space_id, start_time, end_time, status, created_at) VALUES
  (8801, 'usr_001', 1, DATE_ADD(CURDATE(), INTERVAL 14 HOUR), DATE_ADD(CURDATE(), INTERVAL 16 HOUR), 'CONFIRMED', DATE_SUB(NOW(), INTERVAL 1 DAY)),
  (8802, 'usr_002', 2, DATE_ADD(CURDATE(), INTERVAL 18 HOUR), DATE_ADD(CURDATE(), INTERVAL 20 HOUR), 'CONFIRMED', DATE_ADD(DATE_SUB(NOW(), INTERVAL 1 DAY), INTERVAL 2 HOUR)),
  (8803, 'usr_003', 4, DATE_ADD(CURDATE(), INTERVAL 16 HOUR), DATE_ADD(CURDATE(), INTERVAL 18 HOUR), 'CONFIRMED', DATE_SUB(NOW(), INTERVAL 20 HOUR)),
  (8804, 'usr_001', 3, DATE_ADD(DATE_ADD(CURDATE(), INTERVAL 1 DAY), INTERVAL 12 HOUR), DATE_ADD(DATE_ADD(CURDATE(), INTERVAL 1 DAY), INTERVAL 14 HOUR), 'CONFIRMED', DATE_SUB(NOW(), INTERVAL 3 HOUR)),
  (8805, 'usr_004', 6, DATE_ADD(DATE_ADD(CURDATE(), INTERVAL 1 DAY), INTERVAL 18 HOUR), DATE_ADD(DATE_ADD(CURDATE(), INTERVAL 1 DAY), INTERVAL 20 HOUR), 'CONFIRMED', DATE_SUB(NOW(), INTERVAL 2 DAY)),
  (8806, 'usr_005', 2, DATE_ADD(CURDATE(), INTERVAL 10 HOUR), DATE_ADD(CURDATE(), INTERVAL 12 HOUR), 'CANCELLED', DATE_SUB(NOW(), INTERVAL 2 DAY)),
  (8807, 'usr_006', 5, DATE_ADD(CURDATE(), INTERVAL 10 HOUR), DATE_ADD(CURDATE(), INTERVAL 12 HOUR), 'CONFIRMED', DATE_ADD(DATE_SUB(NOW(), INTERVAL 1 DAY), INTERVAL 4 HOUR)),
  (8808, 'usr_006', 5, DATE_ADD(CURDATE(), INTERVAL 12 HOUR), DATE_ADD(CURDATE(), INTERVAL 14 HOUR), 'CONFIRMED', DATE_ADD(DATE_SUB(NOW(), INTERVAL 1 DAY), INTERVAL 4 HOUR)),
  (8809, 'usr_007', 3, DATE_ADD(CURDATE(), INTERVAL 20 HOUR), DATE_ADD(CURDATE(), INTERVAL 22 HOUR), 'CONFIRMED', DATE_SUB(NOW(), INTERVAL 5 HOUR));

INSERT INTO ReservationEquipment (reservation_id, equipment_id) VALUES
  (8801, 1),
  (8801, 3),
  (8802, 2),
  (8803, 1),
  (8804, 4),
  (8805, 3),
  (8807, 4),
  (8809, 2);
