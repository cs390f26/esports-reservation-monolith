SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS ReservationEquipment;
DROP TABLE IF EXISTS Reservations;
DROP TABLE IF EXISTS Equipment;
DROP TABLE IF EXISTS Computers;
DROP TABLE IF EXISTS Spaces;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE Spaces (
  space_id    INT          NOT NULL AUTO_INCREMENT,
  space_name  VARCHAR(255) NOT NULL,
  description TEXT,
  is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
  PRIMARY KEY (space_id)
);

CREATE TABLE Computers (
  computer_id INT          NOT NULL AUTO_INCREMENT,
  space_id    INT          NOT NULL,
  hostname    VARCHAR(255) NOT NULL,
  specs       TEXT,
  status      VARCHAR(255) NOT NULL DEFAULT 'AVAILABLE',
  PRIMARY KEY (computer_id),
  CONSTRAINT fk_computers_space FOREIGN KEY (space_id) REFERENCES Spaces (space_id),
  CONSTRAINT chk_computer_status CHECK (status IN ('AVAILABLE', 'IN_USE', 'MAINTENANCE', 'OFFLINE'))
);

CREATE TABLE Equipment (
  equipment_id  INT          NOT NULL AUTO_INCREMENT,
  item_name     VARCHAR(255) NOT NULL,
  category      VARCHAR(255) NOT NULL,
  serial_number VARCHAR(255),
  status        VARCHAR(255) NOT NULL DEFAULT 'AVAILABLE',
  PRIMARY KEY (equipment_id),
  CONSTRAINT chk_equipment_category CHECK (category IN ('HEADSET', 'CONTROLLER')),
  CONSTRAINT chk_equipment_status CHECK (status IN ('AVAILABLE', 'IN_USE', 'MAINTENANCE', 'OFFLINE'))
);

-- Each reservation covers one 2-hour block. The application derives start_time and
-- end_time from the requested date and start hour (10, 12, 14, 16, 18, or 20).
CREATE TABLE Reservations (
  reservation_id INT          NOT NULL AUTO_INCREMENT,
  user_name      VARCHAR(255) NOT NULL,
  space_id       INT          NOT NULL,
  start_time     DATETIME     NOT NULL,
  end_time       DATETIME     NOT NULL,
  status         VARCHAR(255) NOT NULL DEFAULT 'CONFIRMED',
  created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  confirmed_slot VARCHAR(64) GENERATED ALWAYS AS (
    CASE
      WHEN status = 'CONFIRMED'
        THEN CONCAT(space_id, '#', DATE_FORMAT(start_time, '%Y-%m-%d %H:%i:%s'))
      ELSE NULL
    END
  ) STORED,
  PRIMARY KEY (reservation_id),
  CONSTRAINT fk_reservations_space FOREIGN KEY (space_id) REFERENCES Spaces (space_id),
  CONSTRAINT chk_reservation_status CHECK (status IN ('CONFIRMED', 'CANCELLED', 'COMPLETED')),
  CONSTRAINT chk_reservation_times CHECK (end_time > start_time),
  UNIQUE KEY one_confirmed_booking_per_space (confirmed_slot)
);

CREATE TABLE ReservationEquipment (
  reservation_id INT NOT NULL,
  equipment_id   INT NOT NULL,
  PRIMARY KEY (reservation_id, equipment_id),
  CONSTRAINT fk_reservation_equipment_reservation
    FOREIGN KEY (reservation_id) REFERENCES Reservations (reservation_id),
  CONSTRAINT fk_reservation_equipment_item
    FOREIGN KEY (equipment_id) REFERENCES Equipment (equipment_id)
);

CREATE INDEX reservation_equipment_by_item ON ReservationEquipment (equipment_id);
