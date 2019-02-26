USE `smart_running_helper`;

DROP TABLE IF EXISTS `user_sport_database`;
CREATE TABLE IF NOT EXISTS `user_sport_database` (
	`UserID` CHAR(50) NOT NULL,
	`Time` DATETIME(2) NOT NULL DEFAULT CURRENT_TIMESTAMP(2),
	`Tag` CHAR(50) NOT NULL,
	`gyro_x` FLOAT NOT NULL,
	`gyro_y` FLOAT NOT NULL,
	`gyro_z` FLOAT NOT NULL,
	`accel_x` FLOAT NOT NULL,
	`accel_y` FLOAT NOT NULL,
	`accel_z` FLOAT NOT NULL,
	`rotation_x` FLOAT NOT NULL,
	`rotation_y` FLOAT NOT NULL,
	`gyro_x_std` FLOAT NOT NULL,
	`gyro_y_std` FLOAT NOT NULL,
	`gyro_z_std` FLOAT NOT NULL,
	`accel_x_std` FLOAT NOT NULL,
	`accel_y_std` FLOAT NOT NULL,
	`accel_z_std` FLOAT NOT NULL,
	`rotation_x_std` FLOAT NOT NULL,
	`rotation_y_std` FLOAT NOT NULL
)
COLLATE='utf8_general_ci'
ENGINE=InnoDB
;

