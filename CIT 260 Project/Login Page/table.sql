CREATE TABLE user (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL
);

INSERT INTO user (username, password_hash)
VALUES ('55555@student.csn.edu', '55555');

INSERT INTO user (username, password_hash)
VALUES ('44444@student.csn.edu', '44444');