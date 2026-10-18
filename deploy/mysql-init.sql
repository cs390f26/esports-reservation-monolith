-- The app user creates a database per test run, so it needs more than the one
-- schema Docker creates for MYSQL_DATABASE.
GRANT ALL PRIVILEGES ON *.* TO 'esports'@'%' WITH GRANT OPTION;
GRANT SYSTEM_VARIABLES_ADMIN ON *.* TO 'esports'@'%';
FLUSH PRIVILEGES;
