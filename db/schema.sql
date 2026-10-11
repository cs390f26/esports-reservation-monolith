DROP TABLE IF EXISTS ReservationEquipment;
DROP TABLE IF EXISTS Reservations;
DROP TABLE IF EXISTS Equipment;
DROP TABLE IF EXISTS Computers;
DROP TABLE IF EXISTS Spaces;

CREATE TABLE Spaces (
  space_id    INTEGER      PRIMARY KEY,
  space_name  VARCHAR(255) NOT NULL,
  description TEXT,
  is_active   BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE TABLE Computers (
  computer_id INTEGER      PRIMARY KEY,
  space_id    INTEGER      NOT NULL REFERENCES Spaces (space_id),
  hostname    VARCHAR(255) NOT NULL,
  specs       TEXT,
  status      VARCHAR(255) NOT NULL DEFAULT 'AVAILABLE'
    CHECK (status IN ('AVAILABLE', 'IN_USE', 'MAINTENANCE', 'OFFLINE'))
);

CREATE TABLE Equipment (
  equipment_id  INTEGER      PRIMARY KEY,
  item_name     VARCHAR(255) NOT NULL,
  category      VARCHAR(255) NOT NULL CHECK (category IN ('HEADSET', 'CONTROLLER')),
  serial_number VARCHAR(255),
  status        VARCHAR(255) NOT NULL DEFAULT 'AVAILABLE'
    CHECK (status IN ('AVAILABLE', 'IN_USE', 'MAINTENANCE', 'OFFLINE'))
);

-- Each reservation covers one 2-hour block. The application derives start_time and
-- end_time from the requested date and start hour (10, 12, 14, 16, 18, or 20).
CREATE TABLE Reservations (
  reservation_id INTEGER      PRIMARY KEY,
  user_name      VARCHAR(255) NOT NULL,
  space_id       INTEGER      NOT NULL REFERENCES Spaces (space_id),
  start_time     TIMESTAMP    NOT NULL,
  end_time       TIMESTAMP    NOT NULL,
  status         VARCHAR(255) NOT NULL DEFAULT 'CONFIRMED'
    CHECK (status IN ('CONFIRMED', 'CANCELLED', 'COMPLETED')),
  created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (end_time > start_time)
);


CREATE UNIQUE INDEX one_confirmed_booking_per_space
  ON Reservations (space_id, start_time)
  WHERE status = 'CONFIRMED';

CREATE TABLE ReservationEquipment (
  reservation_id INTEGER NOT NULL REFERENCES Reservations (reservation_id),
  equipment_id   INTEGER NOT NULL REFERENCES Equipment (equipment_id),
  PRIMARY KEY (reservation_id, equipment_id)
);

CREATE INDEX reservation_equipment_by_item ON ReservationEquipment (equipment_id);
